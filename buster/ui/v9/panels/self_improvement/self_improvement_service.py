from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .session.repair_session import (
    RepairSession,
    RepairSessionStage,
    RepairSessionStatus,
)
from .session.session_manager import RepairSessionManager


StageHandler = Callable[[RepairSession], Any]
EventPublisher = Callable[[str, Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class RepairWorkflowHandlers:
    """
    Backend handlers used by SelfImprovementService.

    Each handler performs exactly one repair stage and returns its result.
    Handlers must not mutate RepairSession directly and must not decide which
    workflow stage runs next.
    """

    review: Optional[StageHandler] = None
    plan: Optional[StageHandler] = None
    preview: Optional[StageHandler] = None
    apply: Optional[StageHandler] = None
    verify: Optional[StageHandler] = None
    rollback: Optional[StageHandler] = None
    history: Optional[StageHandler] = None


@dataclass(frozen=True, slots=True)
class RepairTask:
    session_id: str
    stage: str
    future: Future[Any]


class SelfImprovementService:
    """
    Orchestrates the complete repair lifecycle.

    Responsibilities:
        - expose the public repair workflow API
        - create and resume RepairSession instances
        - start one backend stage at a time
        - record stage results through RepairSessionManager
        - optionally advance safe non-destructive stages automatically
        - require explicit approval before applying changes
        - route failures into the canonical session state
        - publish workflow-level events

    This service contains no UI logic. It does not update widgets and does not
    depend on PySide6. SelfImprovementPanel should call this public API and
    subscribe to Event Bus updates.

    The manager remains the only authority that mutates and persists sessions.
    """

    ACTIVE_STAGE_STATUSES = frozenset(
        {
            RepairSessionStatus.REVIEWING.value,
            RepairSessionStatus.PLANNING.value,
            RepairSessionStatus.PREVIEWING.value,
            RepairSessionStatus.APPLYING.value,
            RepairSessionStatus.VERIFYING.value,
            RepairSessionStatus.ROLLING_BACK.value,
        }
    )

    def __init__(
        self,
        project_root: str | Path,
        *,
        session_manager: Optional[RepairSessionManager] = None,
        handlers: Optional[RepairWorkflowHandlers] = None,
        event_bus: Any = None,
        event_publisher: Optional[EventPublisher] = None,
        max_workers: int = 3,
        auto_review: bool = True,
        auto_plan: bool = True,
        auto_preview: bool = True,
        auto_verify: bool = True,
        auto_complete: bool = True,
        rollback_on_verification_failure: bool = False,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

        self._event_bus = event_bus
        self._event_publisher = event_publisher

        self.session_manager = session_manager or RepairSessionManager(
            self.project_root,
            event_bus=event_bus,
            event_publisher=event_publisher,
        )

        self.handlers = handlers or RepairWorkflowHandlers()

        self.auto_review = bool(auto_review)
        self.auto_plan = bool(auto_plan)
        self.auto_preview = bool(auto_preview)
        self.auto_verify = bool(auto_verify)
        self.auto_complete = bool(auto_complete)
        self.rollback_on_verification_failure = bool(
            rollback_on_verification_failure
        )

        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="buster-repair",
        )
        self._lock = threading.RLock()
        self._tasks: dict[str, RepairTask] = {}
        self._closed = False

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_handlers(
        self,
        handlers: RepairWorkflowHandlers,
    ) -> None:
        if not isinstance(handlers, RepairWorkflowHandlers):
            raise TypeError(
                "handlers must be a RepairWorkflowHandlers instance."
            )

        with self._lock:
            self.handlers = handlers

    def configure(
        self,
        *,
        auto_review: Optional[bool] = None,
        auto_plan: Optional[bool] = None,
        auto_preview: Optional[bool] = None,
        auto_verify: Optional[bool] = None,
        auto_complete: Optional[bool] = None,
        rollback_on_verification_failure: Optional[bool] = None,
    ) -> None:
        with self._lock:
            if auto_review is not None:
                self.auto_review = bool(auto_review)

            if auto_plan is not None:
                self.auto_plan = bool(auto_plan)

            if auto_preview is not None:
                self.auto_preview = bool(auto_preview)

            if auto_verify is not None:
                self.auto_verify = bool(auto_verify)

            if auto_complete is not None:
                self.auto_complete = bool(auto_complete)

            if rollback_on_verification_failure is not None:
                self.rollback_on_verification_failure = bool(
                    rollback_on_verification_failure
                )

    # ------------------------------------------------------------------
    # Public session API
    # ------------------------------------------------------------------

    def start_repair(
        self,
        finding: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
        start_review: Optional[bool] = None,
    ) -> RepairSession:
        self._ensure_open()

        session = self.session_manager.create_session(
            finding,
            metadata=metadata,
            session_id=session_id,
        )

        self._publish(
            "repair.started",
            self._payload(
                session,
                {
                    "finding": session.finding,
                },
            ),
        )

        should_start_review = (
            self.auto_review
            if start_review is None
            else bool(start_review)
        )

        if should_start_review:
            self.review(session.session_id)

        return session

    def get_session(
        self,
        session_id: str,
        *,
        reload: bool = False,
    ) -> RepairSession:
        return self.session_manager.get_session(
            session_id,
            reload=reload,
        )

    def latest_session(
        self,
        *,
        include_completed: bool = True,
    ) -> RepairSession | None:
        return self.session_manager.latest_session(
            include_completed=include_completed
        )

    def active_sessions(self) -> list[RepairSession]:
        return self.session_manager.list_active_sessions()

    def all_sessions(self) -> list[RepairSession]:
        return self.session_manager.list_sessions(
            include_completed=True
        )

    # ------------------------------------------------------------------
    # Stage commands
    # ------------------------------------------------------------------

    def review(
        self,
        session_id: str,
    ) -> RepairTask:
        session = self.get_session(session_id)

        self._require_status(
            session,
            RepairSessionStatus.CREATED,
        )
        self._require_handler("review")

        self.session_manager.start_review(session_id)
        return self._submit(
            session_id,
            RepairSessionStage.REVIEW,
            self.handlers.review,
            self._review_succeeded,
        )

    def plan(
        self,
        session_id: str,
    ) -> RepairTask:
        session = self.get_session(session_id)

        self._require_status(
            session,
            RepairSessionStatus.REVIEWED,
        )
        self._require_handler("plan")

        self.session_manager.start_plan(session_id)
        return self._submit(
            session_id,
            RepairSessionStage.PLAN,
            self.handlers.plan,
            self._plan_succeeded,
        )

    def preview(
        self,
        session_id: str,
    ) -> RepairTask:
        session = self.get_session(session_id)

        self._require_status(
            session,
            RepairSessionStatus.PLANNED,
        )
        self._require_handler("preview")

        self.session_manager.start_preview(session_id)
        return self._submit(
            session_id,
            RepairSessionStage.PREVIEW,
            self.handlers.preview,
            self._preview_succeeded,
        )

    def approve(
        self,
        session_id: str,
        *,
        apply_immediately: bool = False,
    ) -> RepairSession:
        session = self.get_session(session_id)

        self._require_status(
            session,
            RepairSessionStatus.PREVIEW_READY,
        )

        session = self.session_manager.approve_preview(session_id)

        self._publish(
            "repair.approved",
            self._payload(session),
        )

        if apply_immediately:
            self.apply(session_id)

        return session

    def reject(
        self,
        session_id: str,
        reason: str = "Preview rejected by the user.",
    ) -> RepairSession:
        session = self.session_manager.reject_preview(
            session_id,
            reason,
        )

        self._publish(
            "repair.rejected",
            self._payload(
                session,
                {"reason": reason},
            ),
        )
        return session

    def apply(
        self,
        session_id: str,
    ) -> RepairTask:
        session = self.get_session(session_id)

        self._require_status(
            session,
            RepairSessionStatus.APPROVED,
        )
        self._require_handler("apply")

        self.session_manager.start_apply(session_id)
        return self._submit(
            session_id,
            RepairSessionStage.APPLY,
            self.handlers.apply,
            self._apply_succeeded,
        )

    def verify(
        self,
        session_id: str,
    ) -> RepairTask:
        session = self.get_session(session_id)

        self._require_status(
            session,
            RepairSessionStatus.APPLIED,
        )
        self._require_handler("verify")

        self.session_manager.start_verification(session_id)
        return self._submit(
            session_id,
            RepairSessionStage.VERIFICATION,
            self.handlers.verify,
            self._verification_succeeded,
        )

    def rollback(
        self,
        session_id: str,
    ) -> RepairTask:
        session = self.get_session(session_id)

        allowed = {
            RepairSessionStatus.APPLYING.value,
            RepairSessionStatus.APPLIED.value,
            RepairSessionStatus.VERIFYING.value,
            RepairSessionStatus.VERIFIED.value,
            RepairSessionStatus.VERIFICATION_FAILED.value,
            RepairSessionStatus.FAILED.value,
        }

        if session.status not in allowed:
            raise RuntimeError(
                "Rollback is unavailable while repair session status is "
                f"{session.status!r}."
            )

        self._require_handler("rollback")

        self.session_manager.start_rollback(session_id)
        return self._submit(
            session_id,
            RepairSessionStage.ROLLBACK,
            self.handlers.rollback,
            self._rollback_succeeded,
        )

    def complete(
        self,
        session_id: str,
        message: str = "Repair session completed.",
    ) -> RepairSession:
        session = self.get_session(session_id)

        if self.handlers.history is not None and not session.history_record:
            history = self.handlers.history(session)
            self.session_manager.record_history(
                session_id,
                self._normalise_result(history),
            )

        return self.session_manager.complete_session(
            session_id,
            message,
        )

    def cancel(
        self,
        session_id: str,
        reason: str = "Repair session cancelled.",
    ) -> RepairSession:
        self.cancel_running_task(session_id)
        session = self.session_manager.cancel_session(
            session_id,
            reason,
        )

        self._publish(
            "repair.cancelled",
            self._payload(
                session,
                {"reason": reason},
            ),
        )
        return session

    # ------------------------------------------------------------------
    # Worker result callbacks
    # ------------------------------------------------------------------

    def record_review_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._review_succeeded(
            session_id,
            self._normalise_result(result),
        )

    def record_plan_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._plan_succeeded(
            session_id,
            self._normalise_result(result),
        )

    def record_preview_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._preview_succeeded(
            session_id,
            self._normalise_result(result),
        )

    def record_apply_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._apply_succeeded(
            session_id,
            self._normalise_result(result),
        )

    def record_verification_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._verification_succeeded(
            session_id,
            self._normalise_result(result),
        )

    def record_rollback_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._rollback_succeeded(
            session_id,
            self._normalise_result(result),
        )

    def report_stage_failure(
        self,
        session_id: str,
        stage: RepairSessionStage | str,
        error: str | BaseException,
        *,
        data: Optional[Mapping[str, Any]] = None,
    ) -> RepairSession:
        message = str(error)

        session = self.session_manager.fail_session(
            session_id,
            message,
            stage=stage,
            data=data,
        )

        self._publish(
            "repair.stage.failed",
            self._payload(
                session,
                {
                    "stage": (
                        stage.value
                        if isinstance(stage, RepairSessionStage)
                        else str(stage)
                    ),
                    "error": message,
                    "data": dict(data or {}),
                },
            ),
        )
        return session

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover_sessions(
        self,
    ) -> list[RepairSession]:
        """
        Load incomplete sessions without blindly restarting destructive work.

        Safe states may resume automatically:
            CREATED -> review
            REVIEWED -> plan
            PLANNED -> preview
            APPLIED -> verify

        Approval, apply and rollback states require an explicit caller action.
        Sessions interrupted in a running state remain persisted and are
        surfaced through repair.recovery.action_required.
        """
        sessions = self.session_manager.resume_incomplete_sessions()

        for session in sessions:
            try:
                if (
                    session.status == RepairSessionStatus.CREATED.value
                    and self.auto_review
                    and self.handlers.review is not None
                ):
                    self.review(session.session_id)

                elif (
                    session.status == RepairSessionStatus.REVIEWED.value
                    and self.auto_plan
                    and self.handlers.plan is not None
                ):
                    self.plan(session.session_id)

                elif (
                    session.status == RepairSessionStatus.PLANNED.value
                    and self.auto_preview
                    and self.handlers.preview is not None
                ):
                    self.preview(session.session_id)

                elif (
                    session.status == RepairSessionStatus.APPLIED.value
                    and self.auto_verify
                    and self.handlers.verify is not None
                ):
                    self.verify(session.session_id)

                elif session.status in self.ACTIVE_STAGE_STATUSES:
                    self._publish(
                        "repair.recovery.action_required",
                        self._payload(
                            session,
                            {
                                "reason": (
                                    "The application stopped while this "
                                    "stage was running."
                                ),
                            },
                        ),
                    )

            except Exception as exc:
                self._publish(
                    "repair.recovery.failed",
                    self._payload(
                        session,
                        {"error": str(exc)},
                    ),
                )

        return sessions

    # ------------------------------------------------------------------
    # Task inspection and shutdown
    # ------------------------------------------------------------------

    def running_task(
        self,
        session_id: str,
    ) -> Optional[RepairTask]:
        with self._lock:
            task = self._tasks.get(str(session_id))

            if task is None or task.future.done():
                return None

            return task

    def running_tasks(self) -> list[RepairTask]:
        with self._lock:
            return [
                task
                for task in self._tasks.values()
                if not task.future.done()
            ]

    def cancel_running_task(
        self,
        session_id: str,
    ) -> bool:
        with self._lock:
            task = self._tasks.get(str(session_id))

            if task is None:
                return False

            cancelled = task.future.cancel()

            if cancelled:
                self._tasks.pop(str(session_id), None)

            return cancelled

    def shutdown(
        self,
        *,
        wait: bool = False,
        cancel_futures: bool = True,
    ) -> None:
        with self._lock:
            if self._closed:
                return

            self._closed = True

        self._executor.shutdown(
            wait=wait,
            cancel_futures=cancel_futures,
        )

    # ------------------------------------------------------------------
    # Successful stage handling
    # ------------------------------------------------------------------

    def _review_succeeded(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        session = self.session_manager.record_review(
            session_id,
            self._normalise_result(result),
        )

        if self.auto_plan and self.handlers.plan is not None:
            self.plan(session_id)

        return session

    def _plan_succeeded(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        session = self.session_manager.record_plan(
            session_id,
            self._normalise_result(result),
        )

        if self.auto_preview and self.handlers.preview is not None:
            self.preview(session_id)

        return session

    def _preview_succeeded(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        # The workflow intentionally stops here for explicit approval.
        return self.session_manager.record_preview(
            session_id,
            self._normalise_result(result),
        )

    def _apply_succeeded(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        session = self.session_manager.record_apply_result(
            session_id,
            self._normalise_result(result),
        )

        if self.auto_verify and self.handlers.verify is not None:
            self.verify(session_id)

        return session

    def _verification_succeeded(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        session = self.session_manager.record_verification(
            session_id,
            self._normalise_result(result),
        )

        if session.verification_passed:
            if self.auto_complete:
                return self.complete(
                    session_id,
                    "Repair verified and completed.",
                )

        elif (
            self.rollback_on_verification_failure
            and self.handlers.rollback is not None
        ):
            self.rollback(session_id)

        return session

    def _rollback_succeeded(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        session = self.session_manager.record_rollback(
            session_id,
            self._normalise_result(result),
        )

        if (
            session.status == RepairSessionStatus.ROLLED_BACK.value
            and self.auto_complete
        ):
            return self.complete(
                session_id,
                "Repair rolled back and session completed.",
            )

        return session

    # ------------------------------------------------------------------
    # Background execution
    # ------------------------------------------------------------------

    def _submit(
        self,
        session_id: str,
        stage: RepairSessionStage,
        handler: Optional[StageHandler],
        success_callback: Callable[[str, Any], RepairSession],
    ) -> RepairTask:
        self._ensure_open()

        if handler is None:
            raise RuntimeError(
                f"No handler is configured for stage {stage.value!r}."
            )

        normalized = str(session_id)

        with self._lock:
            existing = self._tasks.get(normalized)

            if existing is not None and not existing.future.done():
                raise RuntimeError(
                    "A repair task is already running for session "
                    f"{normalized}."
                )

            future = self._executor.submit(
                self._execute_handler,
                normalized,
                stage,
                handler,
            )

            task = RepairTask(
                session_id=normalized,
                stage=stage.value,
                future=future,
            )
            self._tasks[normalized] = task

        future.add_done_callback(
            lambda completed: self._task_finished(
                normalized,
                stage,
                completed,
                success_callback,
            )
        )

        return task

    def _execute_handler(
        self,
        session_id: str,
        stage: RepairSessionStage,
        handler: StageHandler,
    ) -> Any:
        session = self.get_session(session_id)

        self._publish(
            "repair.stage.executing",
            self._payload(
                session,
                {"stage": stage.value},
            ),
        )

        return handler(session)

    def _task_finished(
        self,
        session_id: str,
        stage: RepairSessionStage,
        future: Future[Any],
        success_callback: Callable[[str, Any], RepairSession],
    ) -> None:
        with self._lock:
            current = self._tasks.get(session_id)

            if current is not None and current.future is future:
                self._tasks.pop(session_id, None)

        if future.cancelled():
            self._publish(
                "repair.stage.cancelled",
                {
                    "session_id": session_id,
                    "stage": stage.value,
                },
            )
            return

        try:
            result = future.result()
            success_callback(session_id, result)

        except Exception as exc:
            try:
                self.report_stage_failure(
                    session_id,
                    stage,
                    exc,
                )
            except Exception:
                self._publish(
                    "repair.stage.failure_unrecorded",
                    {
                        "session_id": session_id,
                        "stage": stage.value,
                        "error": str(exc),
                    },
                )

    # ------------------------------------------------------------------
    # Validation and conversion
    # ------------------------------------------------------------------

    def _require_status(
        self,
        session: RepairSession,
        required: RepairSessionStatus,
    ) -> None:
        if session.status != required.value:
            raise RuntimeError(
                f"Repair session {session.session_id} must be "
                f"{required.value!r}, not {session.status!r}."
            )

    def _require_handler(
        self,
        name: str,
    ) -> StageHandler:
        handler = getattr(self.handlers, name, None)

        if not callable(handler):
            raise RuntimeError(
                f"Self Improvement handler {name!r} is not configured."
            )

        return handler

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                "SelfImprovementService has been shut down."
            )

    @staticmethod
    def _normalise_result(
        value: Any,
    ) -> dict[str, Any]:
        if value is None:
            return {}

        if isinstance(value, Mapping):
            return dict(value)

        method = getattr(value, "to_dict", None)

        if callable(method):
            result = method()

            if isinstance(result, Mapping):
                return dict(result)

        # PreviewDiff and similar result objects may expose useful instance
        # attributes without implementing Mapping.
        attributes = getattr(value, "__dict__", None)

        if isinstance(attributes, Mapping):
            return {
                str(key): item
                for key, item in attributes.items()
                if not str(key).startswith("_")
            }

        return {"value": value}

    # ------------------------------------------------------------------
    # Event publication
    # ------------------------------------------------------------------

    def _payload(
        self,
        session: RepairSession,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = {
            "session_id": session.session_id,
            "project_root": session.project_root,
            "status": session.status,
            "progress_percent": session.progress_percent,
            "change_id": session.change_id,
            "error": session.error,
            "updated_at": session.updated_at,
            "completed_at": session.completed_at,
            "stage_states": session.stage_states(),
        }

        if extra:
            payload.update(dict(extra))

        return payload

    def _publish(
        self,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        """
        Publish workflow events without depending on one dispatcher shape.

        Supported APIs:
            event_publisher(event_type, payload)
            event_bus.publish(event_type, payload)
            event_bus.publish(event_type, payload, source="self_improvement")
            event_bus.emit(event_type, payload)
            event_bus.dispatch(event_type, payload)
        """
        try:
            if self._event_publisher is not None:
                self._event_publisher(
                    str(event_type),
                    dict(payload),
                )
                return

            if self._event_bus is None:
                return

            publish = getattr(self._event_bus, "publish", None)

            if callable(publish):
                try:
                    publish(
                        str(event_type),
                        dict(payload),
                        source="self_improvement",
                    )
                except TypeError:
                    publish(
                        str(event_type),
                        dict(payload),
                    )
                return

            for method_name in ("emit", "dispatch"):
                method = getattr(
                    self._event_bus,
                    method_name,
                    None,
                )

                if callable(method):
                    method(
                        str(event_type),
                        dict(payload),
                    )
                    return

        except Exception:
            # Event reporting is observational. Subscriber failures must not
            # corrupt persisted repair state.
            return


__all__ = [
    "RepairTask",
    "RepairWorkflowHandlers",
    "SelfImprovementService",
]
