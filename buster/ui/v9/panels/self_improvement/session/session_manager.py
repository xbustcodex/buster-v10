from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .repair_session import (
    RepairSession,
    RepairSessionStage,
    RepairSessionStatus,
)
from .repair_session_store import RepairSessionStore


EventPublisher = Callable[[str, Mapping[str, Any]], None]


class RepairSessionManager:
    """
    Thread-safe owner of persisted RepairSession state.

    Responsibilities:
        - create, load, cache, save, list and delete sessions
        - serialize all session mutations through an RLock
        - expose one method for each repair lifecycle operation
        - persist immediately after every successful mutation
        - publish optional Event Bus lifecycle notifications
        - recover incomplete sessions after application restart

    Worker orchestration does not belong here. Workers execute one operation
    and report the result through this manager. SelfImprovementService decides
    which operation should run next.
    """

    def __init__(
        self,
        project_root: str | Path,
        sessions_root: str | Path | None = None,
        *,
        event_bus: Any = None,
        event_publisher: Optional[EventPublisher] = None,
        preload_active: bool = True,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

        self.store = RepairSessionStore(
            project_root=self.project_root,
            sessions_root=sessions_root,
        )

        self._event_bus = event_bus
        self._event_publisher = event_publisher
        self._lock = threading.RLock()
        self._sessions: dict[str, RepairSession] = {}

        if preload_active:
            self._preload_active_sessions()

    # ------------------------------------------------------------------
    # Creation, loading and persistence
    # ------------------------------------------------------------------

    def create_session(
        self,
        finding: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> RepairSession:
        with self._lock:
            session = RepairSession.create(
                project_root=self.project_root,
                finding=finding,
                metadata=metadata,
                session_id=session_id,
            )

            if session.session_id in self._sessions:
                raise ValueError(
                    f"Repair session already exists: {session.session_id}"
                )

            self._sessions[session.session_id] = session
            self._save_locked(session)

        self._publish_session_event(
            "repair.session.created",
            session,
            {
                "finding": session.finding,
            },
        )
        return session

    def get_session(
        self,
        session_id: str,
        *,
        reload: bool = False,
    ) -> RepairSession:
        normalized = self._normalize_session_id(session_id)

        with self._lock:
            if not reload:
                cached = self._sessions.get(normalized)
                if cached is not None:
                    return cached

            session = self.store.load(normalized)
            self._sessions[normalized] = session
            return session

    def save_session(
        self,
        session: RepairSession,
    ) -> Path:
        if not isinstance(session, RepairSession):
            raise TypeError("session must be a RepairSession instance.")

        with self._lock:
            self._sessions[session.session_id] = session
            path = self._save_locked(session)

        self._publish_session_event(
            "repair.session.saved",
            session,
        )
        return path

    def resume_session(
        self,
        session_id: str,
    ) -> RepairSession:
        session = self.get_session(session_id, reload=True)

        self._publish_session_event(
            "repair.session.resumed",
            session,
        )
        return session

    def latest_session(
        self,
        *,
        include_completed: bool = True,
    ) -> RepairSession | None:
        with self._lock:
            session = self.store.latest(
                include_completed=include_completed
            )

            if session is not None:
                self._sessions[session.session_id] = session

            return session

    def list_active_sessions(self) -> list[RepairSession]:
        with self._lock:
            sessions = self.store.active_sessions()

            for session in sessions:
                self._sessions[session.session_id] = session

            return sessions

    def list_sessions(
        self,
        *,
        include_completed: bool = True,
    ) -> list[RepairSession]:
        with self._lock:
            sessions = self.store.list_sessions(
                include_completed=include_completed
            )

            for session in sessions:
                self._sessions[session.session_id] = session

            return sessions

    def delete_session(
        self,
        session_id: str,
    ) -> bool:
        normalized = self._normalize_session_id(session_id)

        with self._lock:
            session = self._sessions.get(normalized)

            if session is None:
                try:
                    session = self.store.load(normalized)
                except Exception:
                    session = None

            deleted = self.store.delete(normalized)

            if deleted:
                self._sessions.pop(normalized, None)

        if deleted:
            payload = {
                "session_id": normalized,
                "project_root": str(self.project_root),
            }

            if session is not None:
                payload.update(self._session_payload(session))

            self._publish(
                "repair.session.deleted",
                payload,
            )

        return deleted

    # ------------------------------------------------------------------
    # Generic mutation and transition API
    # ------------------------------------------------------------------

    def update_session(
        self,
        session_id: str,
        mutator: Callable[[RepairSession], Any],
        *,
        event_type: str = "repair.session.updated",
        event_data: Optional[Mapping[str, Any]] = None,
    ) -> RepairSession:
        if not callable(mutator):
            raise TypeError("mutator must be callable.")

        with self._lock:
            session = self._get_locked(session_id)
            mutator(session)
            self._save_locked(session)

        self._publish_session_event(
            event_type,
            session,
            event_data,
        )
        return session

    def transition(
        self,
        session_id: str,
        status: RepairSessionStatus | str,
        stage: RepairSessionStage | str,
        message: str = "",
        data: Optional[Mapping[str, Any]] = None,
        *,
        complete: bool = False,
    ) -> RepairSession:
        target = (
            status.value
            if isinstance(status, RepairSessionStatus)
            else str(status)
        )
        previous_status = ""

        def mutate(session: RepairSession) -> None:
            nonlocal previous_status
            previous_status = session.status
            session.transition(
                status,
                stage,
                message,
                data,
                complete=complete,
            )

        session = self.update_session(
            session_id,
            mutate,
            event_type="repair.session.status_changed",
            event_data={
                "previous_status": previous_status,
                "status": target,
                "stage": (
                    stage.value
                    if isinstance(stage, RepairSessionStage)
                    else str(stage)
                ),
                "message": message,
                "data": dict(data or {}),
            },
        )

        return session

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def start_review(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "start_review",
            event_type="repair.review.started",
        )

    def record_review(
        self,
        session_id: str,
        review: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_review",
            review,
            event_type="repair.review.completed",
            event_data={"review": self._plain_mapping(review)},
        )

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def start_plan(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "start_plan",
            event_type="repair.plan.started",
        )

    def record_plan(
        self,
        session_id: str,
        plan: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_plan",
            plan,
            event_type="repair.plan.completed",
            event_data={"repair_plan": self._plain_mapping(plan)},
        )

    # ------------------------------------------------------------------
    # Preview and approval
    # ------------------------------------------------------------------

    def start_preview(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "start_preview",
            event_type="repair.preview.started",
        )

    def record_preview(
        self,
        session_id: str,
        preview: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_preview",
            preview,
            event_type="repair.preview.ready",
            event_data={"preview": self._plain_mapping(preview)},
        )

    def approve_preview(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "approve_preview",
            event_type="repair.preview.approved",
        )

    def reject_preview(
        self,
        session_id: str,
        reason: str = "Preview rejected by the user.",
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "reject_preview",
            reason,
            event_type="repair.preview.rejected",
            event_data={"reason": reason},
        )

    # ------------------------------------------------------------------
    # Backup and manifest
    # ------------------------------------------------------------------

    def record_backup(
        self,
        session_id: str,
        backup: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_backup",
            backup,
            event_type="repair.backup.completed",
            event_data={"backup": self._plain_mapping(backup)},
        )

    def record_manifest(
        self,
        session_id: str,
        manifest: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_manifest",
            manifest,
            event_type="repair.manifest.recorded",
            event_data={
                "change_manifest": self._plain_mapping(manifest),
            },
        )

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def start_apply(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "start_apply",
            event_type="repair.apply.started",
        )

    def record_apply_result(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_apply_result",
            result,
            event_type="repair.apply.completed",
            event_data={"apply_result": self._plain_mapping(result)},
        )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def start_verification(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "start_verification",
            event_type="repair.verification.started",
        )

    def record_verification(
        self,
        session_id: str,
        report: Any,
    ) -> RepairSession:
        session = self._run_session_method(
            session_id,
            "record_verification",
            report,
            event_type="repair.verification.completed",
            event_data={
                "verification_report": self._plain_mapping(report),
            },
        )

        if session.verification_passed:
            self._publish_session_event(
                "repair.verification.passed",
                session,
            )
        else:
            self._publish_session_event(
                "repair.verification.failed",
                session,
                {
                    "verification_report": session.verification_report,
                },
            )

        return session

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def start_rollback(
        self,
        session_id: str,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "start_rollback",
            event_type="repair.rollback.started",
        )

    def record_rollback(
        self,
        session_id: str,
        result: Any,
    ) -> RepairSession:
        session = self._run_session_method(
            session_id,
            "record_rollback",
            result,
            event_type="repair.rollback.completed",
            event_data={
                "rollback_result": self._plain_mapping(result),
            },
        )

        if session.status == RepairSessionStatus.FAILED.value:
            self._publish_session_event(
                "repair.rollback.failed",
                session,
                {
                    "rollback_result": session.rollback_result,
                    "error": session.error,
                },
            )

        return session

    # ------------------------------------------------------------------
    # History and terminal operations
    # ------------------------------------------------------------------

    def record_history(
        self,
        session_id: str,
        record: Any,
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "record_history",
            record,
            event_type="repair.history.recorded",
            event_data={
                "history_record": self._plain_mapping(record),
            },
        )

    def complete_session(
        self,
        session_id: str,
        message: str = "Repair session completed.",
    ) -> RepairSession:
        session = self._run_session_method(
            session_id,
            "complete",
            message,
            event_type="repair.session.completed",
            event_data={"message": message},
        )

        self._publish_session_event(
            "repair.finished",
            session,
            {"message": message},
        )
        return session

    def fail_session(
        self,
        session_id: str,
        message: str,
        *,
        stage: RepairSessionStage | str = RepairSessionStage.HISTORY,
        data: Optional[Mapping[str, Any]] = None,
    ) -> RepairSession:
        session = self._run_session_method(
            session_id,
            "fail",
            message,
            stage=stage,
            data=data,
            event_type="repair.session.failed",
            event_data={
                "message": message,
                "stage": (
                    stage.value
                    if isinstance(stage, RepairSessionStage)
                    else str(stage)
                ),
                "data": dict(data or {}),
            },
        )

        self._publish_session_event(
            "repair.failed",
            session,
            {
                "message": message,
                "stage": (
                    stage.value
                    if isinstance(stage, RepairSessionStage)
                    else str(stage)
                ),
            },
        )
        return session

    def cancel_session(
        self,
        session_id: str,
        reason: str = "Repair session cancelled.",
    ) -> RepairSession:
        return self._run_session_method(
            session_id,
            "cancel",
            reason,
            event_type="repair.session.cancelled",
            event_data={"reason": reason},
        )

    # ------------------------------------------------------------------
    # Startup recovery
    # ------------------------------------------------------------------

    def resume_incomplete_sessions(
        self,
    ) -> list[RepairSession]:
        """
        Load all non-terminal sessions and publish recovery notifications.

        This method does not restart workers. SelfImprovementService should
        inspect each returned status and decide whether to resume, retry,
        request approval, rollback, fail safely, or wait for the user.
        """
        sessions = self.list_active_sessions()

        for session in sessions:
            self._publish_session_event(
                "repair.session.recovered",
                session,
                {
                    "recovered_status": session.status,
                },
            )

        return sessions

    def clear_cache(self) -> None:
        with self._lock:
            self._sessions.clear()

    # ------------------------------------------------------------------
    # Backward-compatible API
    # ------------------------------------------------------------------

    def create(
        self,
        finding: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> RepairSession:
        return self.create_session(
            finding,
            metadata=metadata,
            session_id=session_id,
        )

    def save(self, session: RepairSession) -> Path:
        return self.save_session(session)

    def resume(self, session_id: str) -> RepairSession:
        return self.resume_session(session_id)

    def latest(
        self,
        *,
        include_completed: bool = True,
    ) -> RepairSession | None:
        return self.latest_session(
            include_completed=include_completed
        )

    def active(self) -> list[RepairSession]:
        return self.list_active_sessions()

    def list_all(self) -> list[RepairSession]:
        return self.list_sessions(include_completed=True)

    def delete(self, session_id: str) -> bool:
        return self.delete_session(session_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preload_active_sessions(self) -> None:
        try:
            sessions = self.store.active_sessions()
        except Exception:
            return

        with self._lock:
            for session in sessions:
                self._sessions[session.session_id] = session

    def _normalize_session_id(
        self,
        session_id: str,
    ) -> str:
        normalized = str(session_id or "").strip()

        if not normalized:
            raise ValueError("session_id cannot be empty.")

        return normalized

    def _get_locked(
        self,
        session_id: str,
    ) -> RepairSession:
        normalized = self._normalize_session_id(session_id)
        session = self._sessions.get(normalized)

        if session is None:
            session = self.store.load(normalized)
            self._sessions[normalized] = session

        return session

    def _save_locked(
        self,
        session: RepairSession,
    ) -> Path:
        self._sessions[session.session_id] = session
        return self.store.save(session)

    def _run_session_method(
        self,
        session_id: str,
        method_name: str,
        *args: Any,
        event_type: str,
        event_data: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> RepairSession:
        with self._lock:
            session = self._get_locked(session_id)
            method = getattr(session, method_name, None)

            if not callable(method):
                raise AttributeError(
                    f"RepairSession has no callable method "
                    f"{method_name!r}."
                )

            try:
                method(*args, **kwargs)
                self._save_locked(session)
            except Exception as exc:
                self._publish_session_event(
                    "repair.session.operation_failed",
                    session,
                    {
                        "operation": method_name,
                        "error": str(exc),
                    },
                )
                raise

        self._publish_session_event(
            event_type,
            session,
            event_data,
        )
        return session

    def _session_payload(
        self,
        session: RepairSession,
    ) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "project_root": session.project_root,
            "status": session.status,
            "progress_percent": session.progress_percent,
            "updated_at": session.updated_at,
            "completed_at": session.completed_at,
            "error": session.error,
            "change_id": session.change_id,
            "stage_states": session.stage_states(),
        }

    def _publish_session_event(
        self,
        event_type: str,
        session: RepairSession,
        data: Optional[Mapping[str, Any]] = None,
    ) -> None:
        payload = self._session_payload(session)

        if data:
            payload.update(dict(data))

        self._publish(event_type, payload)

    def _publish(
        self,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        """
        Publish without coupling this package to one Event Bus implementation.

        Supported integration styles:
            event_publisher(event_type, payload)
            event_bus.publish(event_type, payload)
            event_bus.emit(event_type, payload)
            event_bus.dispatch(event_type, payload)

        Event publication is observational. A subscriber failure must not
        corrupt or roll back persisted repair session state.
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

            for method_name in ("publish", "emit", "dispatch"):
                method = getattr(self._event_bus, method_name, None)

                if callable(method):
                    method(str(event_type), dict(payload))
                    return
        except Exception:
            return

    @staticmethod
    def _plain_mapping(
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

        return {"value": value}


# Keep the existing import name working while the codebase migrates.
SessionManager = RepairSessionManager


__all__ = [
    "RepairSessionManager",
    "SessionManager",
]
