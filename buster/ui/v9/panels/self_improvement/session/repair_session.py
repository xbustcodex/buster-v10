from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_plain(value: Any) -> Any:
    """
    Convert supported objects into JSON-safe Python values.

    Supports:
        - mappings
        - lists / tuples / sets
        - dataclasses
        - objects exposing to_dict()
        - pathlib.Path
        - enums
    """
    if value is None:
        return None

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): _to_plain(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_to_plain(item) for item in value]

    if is_dataclass(value):
        return _to_plain(asdict(value))

    method = getattr(value, "to_dict", None)
    if callable(method):
        try:
            return _to_plain(method())
        except Exception:
            pass

    return value


class RepairSessionStatus(str, Enum):
    CREATED = "created"
    REVIEWING = "reviewing"
    REVIEWED = "reviewed"
    PLANNING = "planning"
    PLANNED = "planned"
    PREVIEWING = "previewing"
    PREVIEW_READY = "preview_ready"
    APPROVED = "approved"
    APPLYING = "applying"
    APPLIED = "applied"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RepairSessionStage(str, Enum):
    FINDING = "finding"
    REVIEW = "review"
    PLAN = "plan"
    PREVIEW = "preview"
    BACKUP = "backup"
    APPLY = "apply"
    VERIFICATION = "verification"
    ROLLBACK = "rollback"
    HISTORY = "history"


@dataclass
class RepairSessionEvent:
    timestamp: str
    stage: str
    status: str
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        stage: RepairSessionStage | str,
        status: RepairSessionStatus | str,
        message: str = "",
        data: Optional[Mapping[str, Any]] = None,
    ) -> "RepairSessionEvent":
        return cls(
            timestamp=_utc_now(),
            stage=str(
                stage.value
                if isinstance(stage, RepairSessionStage)
                else stage
            ),
            status=str(
                status.value
                if isinstance(status, RepairSessionStatus)
                else status
            ),
            message=str(message or ""),
            data=dict(_to_plain(data or {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "data": _to_plain(self.data),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "RepairSessionEvent":
        return cls(
            timestamp=str(value.get("timestamp") or _utc_now()),
            stage=str(value.get("stage") or ""),
            status=str(value.get("status") or ""),
            message=str(value.get("message") or ""),
            data=dict(value.get("data") or {}),
        )


@dataclass
class RepairSession:
    """
    Single source of truth for one Self Improvement repair workflow.

    A session owns every artifact created during a repair:

        finding
        review
        plan
        preview
        manifest
        apply result
        verification report
        rollback result
        history record

    The object is intentionally JSON serializable so interrupted repairs can
    be persisted and resumed.
    """

    session_id: str
    project_root: str
    status: str = RepairSessionStatus.CREATED.value

    finding: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    preview: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)
    apply_result: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    rollback: dict[str, Any] = field(default_factory=dict)
    history_record: dict[str, Any] = field(default_factory=dict)

    approved: bool = False
    cancelled: bool = False
    error: str = ""

    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    completed_at: str = ""

    events: list[RepairSessionEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        project_root: str | Path,
        finding: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> "RepairSession":
        session = cls(
            session_id=session_id or uuid.uuid4().hex[:12].upper(),
            project_root=str(
                Path(project_root).expanduser().resolve()
            ),
            finding=dict(_to_plain(finding) or {}),
            metadata=dict(_to_plain(metadata or {})),
        )

        session.record_event(
            RepairSessionStage.FINDING,
            RepairSessionStatus.CREATED,
            "Repair session created.",
            {"finding": session.finding},
        )

        return session

    @property
    def change_id(self) -> str:
        return str(
            self.manifest.get("change_id")
            or self.apply_result.get("change_id")
            or ""
        )

    @property
    def is_complete(self) -> bool:
        return self.status in {
            RepairSessionStatus.VERIFIED.value,
            RepairSessionStatus.ROLLED_BACK.value,
            RepairSessionStatus.FAILED.value,
            RepairSessionStatus.CANCELLED.value,
        }

    @property
    def verification_passed(self) -> bool:
        if not self.verification:
            return False

        if self.verification.get("passed") is not None:
            return bool(self.verification.get("passed"))

        return str(
            self.verification.get("status") or ""
        ).lower() in {"passed", "success", "verified"}

    @property
    def progress_percent(self) -> int:
        """
        Return coarse workflow progress for display in the UI.
        """
        weights = {
            RepairSessionStatus.CREATED.value: 5,
            RepairSessionStatus.REVIEWING.value: 12,
            RepairSessionStatus.REVIEWED.value: 22,
            RepairSessionStatus.PLANNING.value: 30,
            RepairSessionStatus.PLANNED.value: 40,
            RepairSessionStatus.PREVIEWING.value: 48,
            RepairSessionStatus.PREVIEW_READY.value: 58,
            RepairSessionStatus.APPROVED.value: 66,
            RepairSessionStatus.APPLYING.value: 74,
            RepairSessionStatus.APPLIED.value: 82,
            RepairSessionStatus.VERIFYING.value: 90,
            RepairSessionStatus.VERIFIED.value: 100,
            RepairSessionStatus.VERIFICATION_FAILED.value: 92,
            RepairSessionStatus.ROLLING_BACK.value: 95,
            RepairSessionStatus.ROLLED_BACK.value: 100,
            RepairSessionStatus.FAILED.value: 100,
            RepairSessionStatus.CANCELLED.value: 100,
        }
        return weights.get(self.status, 0)

    def start_review(self) -> None:
        self.set_status(
            RepairSessionStatus.REVIEWING,
            RepairSessionStage.REVIEW,
            "AI code review started.",
        )

    def set_review(self, review: Any) -> None:
        self.review = dict(_to_plain(review) or {})
        self.set_status(
            RepairSessionStatus.REVIEWED,
            RepairSessionStage.REVIEW,
            "AI code review completed.",
            {"review": self.review},
        )

    def start_plan(self) -> None:
        self.set_status(
            RepairSessionStatus.PLANNING,
            RepairSessionStage.PLAN,
            "Repair planning started.",
        )

    def set_plan(self, plan: Any) -> None:
        self.plan = dict(_to_plain(plan) or {})
        self.set_status(
            RepairSessionStatus.PLANNED,
            RepairSessionStage.PLAN,
            "Repair plan completed.",
            {"plan": self.plan},
        )

    def start_preview(self) -> None:
        self.set_status(
            RepairSessionStatus.PREVIEWING,
            RepairSessionStage.PREVIEW,
            "Preview generation started.",
        )

    def set_preview(self, preview: Any) -> None:
        self.preview = dict(_to_plain(preview) or {})
        self.approved = False
        self.set_status(
            RepairSessionStatus.PREVIEW_READY,
            RepairSessionStage.PREVIEW,
            "Preview is ready for approval.",
            {"preview": self.preview},
        )

    def approve_preview(self) -> None:
        if not self.preview:
            raise RuntimeError(
                "Cannot approve a repair session without a preview."
            )

        self.approved = True
        self.set_status(
            RepairSessionStatus.APPROVED,
            RepairSessionStage.PREVIEW,
            "Preview approved by the user.",
        )

    def reject_preview(
        self,
        reason: str = "Preview rejected by the user.",
    ) -> None:
        self.approved = False
        self.cancel(reason)

    def start_apply(self) -> None:
        if not self.approved:
            raise RuntimeError(
                "Cannot apply a repair before preview approval."
            )

        self.set_status(
            RepairSessionStatus.APPLYING,
            RepairSessionStage.APPLY,
            "Applying approved changes.",
        )

    def set_apply_result(
        self,
        result: Any,
    ) -> None:
        result_dict = dict(_to_plain(result) or {})
        self.apply_result = result_dict

        manifest = result_dict.get("manifest")
        if isinstance(manifest, Mapping):
            self.manifest = dict(manifest)

        self.set_status(
            RepairSessionStatus.APPLIED,
            RepairSessionStage.APPLY,
            str(
                result_dict.get("message")
                or result_dict.get("summary")
                or "Approved changes applied."
            ),
            {"apply_result": result_dict},
        )

    def set_manifest(
        self,
        manifest: Any,
    ) -> None:
        self.manifest = dict(_to_plain(manifest) or {})
        self.touch()

        self.record_event(
            RepairSessionStage.BACKUP,
            self.status,
            "Change manifest attached to repair session.",
            {"change_id": self.change_id},
        )

    def start_verification(self) -> None:
        if not self.apply_result and not self.manifest:
            raise RuntimeError(
                "Cannot verify a repair before changes are applied."
            )

        self.set_status(
            RepairSessionStatus.VERIFYING,
            RepairSessionStage.VERIFICATION,
            "Post-apply verification started.",
        )

    def set_verification(
        self,
        report: Any,
    ) -> None:
        report_dict = dict(_to_plain(report) or {})
        self.verification = report_dict

        passed = bool(
            report_dict.get("passed")
            if "passed" in report_dict
            else str(
                report_dict.get("status") or ""
            ).lower() in {"passed", "success", "verified"}
        )

        if passed:
            self.set_status(
                RepairSessionStatus.VERIFIED,
                RepairSessionStage.VERIFICATION,
                str(
                    report_dict.get("summary")
                    or "Verification passed."
                ),
                {"verification": report_dict},
                complete=True,
            )
        else:
            self.set_status(
                RepairSessionStatus.VERIFICATION_FAILED,
                RepairSessionStage.VERIFICATION,
                str(
                    report_dict.get("summary")
                    or "Verification failed."
                ),
                {"verification": report_dict},
            )

    def start_rollback(self) -> None:
        self.set_status(
            RepairSessionStatus.ROLLING_BACK,
            RepairSessionStage.ROLLBACK,
            "Rollback started.",
        )

    def set_rollback(
        self,
        result: Any,
    ) -> None:
        result_dict = dict(_to_plain(result) or {})
        self.rollback = result_dict

        success = bool(result_dict.get("success"))

        if success:
            self.set_status(
                RepairSessionStatus.ROLLED_BACK,
                RepairSessionStage.ROLLBACK,
                str(
                    result_dict.get("message")
                    or result_dict.get("summary")
                    or "Rollback completed."
                ),
                {"rollback": result_dict},
                complete=True,
            )
        else:
            self.fail(
                str(
                    result_dict.get("message")
                    or result_dict.get("summary")
                    or "Rollback failed."
                ),
                stage=RepairSessionStage.ROLLBACK,
                data={"rollback": result_dict},
            )

    def set_history_record(
        self,
        record: Any,
    ) -> None:
        self.history_record = dict(_to_plain(record) or {})
        self.touch()

        self.record_event(
            RepairSessionStage.HISTORY,
            self.status,
            "History record attached.",
            {"history_record": self.history_record},
        )

    def fail(
        self,
        message: str,
        *,
        stage: RepairSessionStage | str = RepairSessionStage.HISTORY,
        data: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.error = str(message)
        self.set_status(
            RepairSessionStatus.FAILED,
            stage,
            self.error,
            data,
            complete=True,
        )

    def cancel(
        self,
        reason: str = "Repair session cancelled.",
    ) -> None:
        self.cancelled = True
        self.error = str(reason)

        self.set_status(
            RepairSessionStatus.CANCELLED,
            RepairSessionStage.HISTORY,
            self.error,
            complete=True,
        )

    def set_status(
        self,
        status: RepairSessionStatus | str,
        stage: RepairSessionStage | str,
        message: str = "",
        data: Optional[Mapping[str, Any]] = None,
        *,
        complete: bool = False,
    ) -> None:
        self.status = str(
            status.value
            if isinstance(status, RepairSessionStatus)
            else status
        )
        self.touch()

        if complete:
            self.completed_at = _utc_now()

        self.record_event(
            stage,
            self.status,
            message,
            data,
        )

    def record_event(
        self,
        stage: RepairSessionStage | str,
        status: RepairSessionStatus | str,
        message: str = "",
        data: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.events.append(
            RepairSessionEvent.create(
                stage,
                status,
                message,
                data,
            )
        )
        self.touch()

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def stage_states(self) -> dict[str, str]:
        """
        Return a UI-friendly state for every major workflow stage.
        """
        state = {
            RepairSessionStage.FINDING.value: "complete"
            if self.finding
            else "pending",
            RepairSessionStage.REVIEW.value: "complete"
            if self.review
            else "pending",
            RepairSessionStage.PLAN.value: "complete"
            if self.plan
            else "pending",
            RepairSessionStage.PREVIEW.value: "complete"
            if self.preview
            else "pending",
            RepairSessionStage.BACKUP.value: "complete"
            if self.manifest
            else "pending",
            RepairSessionStage.APPLY.value: "complete"
            if self.apply_result
            else "pending",
            RepairSessionStage.VERIFICATION.value: (
                "complete"
                if self.verification_passed
                else "failed"
                if self.verification
                else "pending"
            ),
            RepairSessionStage.ROLLBACK.value: (
                "complete"
                if self.rollback.get("success") is True
                else "failed"
                if self.rollback
                else "not_required"
            ),
            RepairSessionStage.HISTORY.value: "complete"
            if self.history_record
            else "pending",
        }

        return state

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "project_root": self.project_root,
            "status": self.status,
            "finding": _to_plain(self.finding),
            "review": _to_plain(self.review),
            "plan": _to_plain(self.plan),
            "preview": _to_plain(self.preview),
            "manifest": _to_plain(self.manifest),
            "apply_result": _to_plain(self.apply_result),
            "verification": _to_plain(self.verification),
            "rollback": _to_plain(self.rollback),
            "history_record": _to_plain(self.history_record),
            "approved": self.approved,
            "cancelled": self.cancelled,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "events": [
                event.to_dict()
                for event in self.events
            ],
            "metadata": _to_plain(self.metadata),
            "progress_percent": self.progress_percent,
            "stage_states": self.stage_states(),
            "change_id": self.change_id,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "RepairSession":
        session = cls(
            session_id=str(
                value.get("session_id")
                or uuid.uuid4().hex[:12].upper()
            ),
            project_root=str(value.get("project_root") or "."),
            status=str(
                value.get("status")
                or RepairSessionStatus.CREATED.value
            ),
            finding=dict(value.get("finding") or {}),
            review=dict(value.get("review") or {}),
            plan=dict(value.get("plan") or {}),
            preview=dict(value.get("preview") or {}),
            manifest=dict(value.get("manifest") or {}),
            apply_result=dict(value.get("apply_result") or {}),
            verification=dict(value.get("verification") or {}),
            rollback=dict(value.get("rollback") or {}),
            history_record=dict(
                value.get("history_record") or {}
            ),
            approved=bool(value.get("approved")),
            cancelled=bool(value.get("cancelled")),
            error=str(value.get("error") or ""),
            created_at=str(
                value.get("created_at") or _utc_now()
            ),
            updated_at=str(
                value.get("updated_at") or _utc_now()
            ),
            completed_at=str(
                value.get("completed_at") or ""
            ),
            metadata=dict(value.get("metadata") or {}),
        )

        events = value.get("events") or []
        session.events = [
            RepairSessionEvent.from_dict(event)
            for event in events
            if isinstance(event, Mapping)
        ]

        return session

    @classmethod
    def from_value(
        cls,
        value: Any,
    ) -> "RepairSession":
        if isinstance(value, cls):
            return value

        if isinstance(value, Mapping):
            return cls.from_dict(value)

        method = getattr(value, "to_dict", None)
        if callable(method):
            result = method()
            if isinstance(result, Mapping):
                return cls.from_dict(result)

        raise TypeError(
            "RepairSession value must be a RepairSession, mapping, "
            "or object exposing to_dict()."
        )

    def save(
        self,
        path: str | Path,
    ) -> Path:
        output = Path(path).expanduser()
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = output.with_suffix(
            output.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temporary.replace(output)
        return output

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "RepairSession":
        source = Path(path).expanduser()

        data = json.loads(
            source.read_text(encoding="utf-8")
        )

        if not isinstance(data, Mapping):
            raise ValueError(
                "Repair session file must contain a JSON object."
            )

        return cls.from_dict(data)


class RepairSessionStore:
    """
    Persist and discover repair sessions.

    Default storage:

        <project_root>/data/self_improvement/sessions/<session_id>.json
    """

    def __init__(
        self,
        project_root: str | Path,
        sessions_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(
            project_root
        ).expanduser().resolve()

        self.sessions_root = (
            Path(sessions_root).expanduser().resolve()
            if sessions_root is not None
            else self.project_root
            / "data"
            / "self_improvement"
            / "sessions"
        )

        self.sessions_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def session_path(
        self,
        session_id: str,
    ) -> Path:
        safe_id = "".join(
            character
            for character in str(session_id)
            if character.isalnum()
            or character in {"-", "_"}
        )

        if not safe_id:
            raise ValueError("Invalid repair session ID.")

        return self.sessions_root / f"{safe_id}.json"

    def save(
        self,
        session: RepairSession,
    ) -> Path:
        return session.save(
            self.session_path(session.session_id)
        )

    def load(
        self,
        session_id: str,
    ) -> RepairSession:
        return RepairSession.load(
            self.session_path(session_id)
        )

    def delete(
        self,
        session_id: str,
    ) -> bool:
        path = self.session_path(session_id)

        if not path.exists():
            return False

        path.unlink()
        return True

    def list_sessions(
        self,
        *,
        include_completed: bool = True,
    ) -> list[RepairSession]:
        sessions: list[RepairSession] = []

        for path in self.sessions_root.glob("*.json"):
            try:
                session = RepairSession.load(path)
            except Exception:
                continue

            if not include_completed and session.is_complete:
                continue

            sessions.append(session)

        sessions.sort(
            key=lambda item: item.updated_at,
            reverse=True,
        )

        return sessions

    def latest(
        self,
        *,
        include_completed: bool = True,
    ) -> RepairSession | None:
        sessions = self.list_sessions(
            include_completed=include_completed
        )

        return sessions[0] if sessions else None

    def active_sessions(self) -> list[RepairSession]:
        return self.list_sessions(
            include_completed=False
        )


__all__ = [
    "RepairSession",
    "RepairSessionEvent",
    "RepairSessionStage",
    "RepairSessionStatus",
    "RepairSessionStore",
]
