from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    """
    Convert common runtime values into JSON-safe structures.
    """
    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _json_safe(value.to_dict())
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            return _json_safe(vars(value))
        except Exception:
            pass

    return str(value)


@dataclass(slots=True)
class FileChangeRecord:
    """
    Manifest entry for one file involved in an applied change.
    """

    path: str
    backup_path: str = ""
    original_hash: str = ""
    modified_hash: str = ""
    original_size: int = 0
    modified_size: int = 0
    existed_before: bool = True
    exists_after: bool = True
    status: str = "pending"
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "FileChangeRecord":
        if isinstance(value, cls):
            return value

        if hasattr(value, "to_dict") and callable(value.to_dict):
            value = value.to_dict()

        if not isinstance(value, Mapping):
            raise TypeError(
                "FileChangeRecord requires a mapping-compatible value."
            )

        payload = dict(value)

        return cls(
            path=str(payload.get("path") or ""),
            backup_path=str(payload.get("backup_path") or ""),
            original_hash=str(payload.get("original_hash") or ""),
            modified_hash=str(payload.get("modified_hash") or ""),
            original_size=int(payload.get("original_size") or 0),
            modified_size=int(payload.get("modified_size") or 0),
            existed_before=bool(
                payload.get("existed_before", True)
            ),
            exists_after=bool(
                payload.get("exists_after", True)
            ),
            status=str(payload.get("status") or "pending"),
            error=str(payload.get("error") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )

    @staticmethod
    def hash_bytes(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def inspect_file(
        cls,
        path: str | Path,
        *,
        backup_path: str | Path | None = None,
        status: str = "pending",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "FileChangeRecord":
        target = Path(path)
        exists = target.exists() and target.is_file()

        content = target.read_bytes() if exists else b""

        return cls(
            path=str(target),
            backup_path=(
                str(backup_path)
                if backup_path is not None
                else ""
            ),
            original_hash=(
                cls.hash_bytes(content)
                if exists
                else ""
            ),
            original_size=len(content),
            existed_before=exists,
            exists_after=exists,
            status=status,
            metadata=dict(metadata or {}),
        )

    def capture_modified_state(
        self,
        path: str | Path | None = None,
    ) -> None:
        target = Path(path or self.path)
        exists = target.exists() and target.is_file()

        content = target.read_bytes() if exists else b""

        self.modified_hash = (
            self.hash_bytes(content)
            if exists
            else ""
        )
        self.modified_size = len(content)
        self.exists_after = exists

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(slots=True)
class ChangeManifest:
    """
    Durable audit record for a generated, approved, applied, verified,
    rejected, failed, or rolled-back code change.
    """

    change_id: str = field(
        default_factory=lambda: uuid.uuid4().hex
    )
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    status: str = "generated"
    project_root: str = ""
    title: str = ""
    summary: str = ""

    finding: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)

    patch: str = ""
    files: list[FileChangeRecord] = field(default_factory=list)

    approval_required: bool = True
    approved: bool = False
    approved_at: str = ""
    rejected_at: str = ""

    applied_at: str = ""
    verified_at: str = ""
    rolled_back_at: str = ""

    verification: dict[str, Any] = field(default_factory=dict)
    rollback: dict[str, Any] = field(default_factory=dict)

    provider: str = ""
    model: str = ""
    requested_from: str = ""

    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        project_root: str | Path | None = None,
        title: str = "",
        summary: str = "",
        finding: Optional[Mapping[str, Any]] = None,
        review: Optional[Mapping[str, Any]] = None,
        plan: Optional[Mapping[str, Any]] = None,
        patch: str = "",
        files: Optional[Iterable[Any]] = None,
        provider: str = "",
        model: str = "",
        requested_from: str = "",
        approval_required: bool = True,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "ChangeManifest":
        return cls(
            project_root=(
                str(Path(project_root).expanduser().resolve())
                if project_root
                else ""
            ),
            title=str(title or ""),
            summary=str(summary or ""),
            finding=dict(finding or {}),
            review=dict(review or {}),
            plan=dict(plan or {}),
            patch=str(patch or ""),
            files=[
                FileChangeRecord.from_value(item)
                for item in (files or [])
            ],
            provider=str(provider or ""),
            model=str(model or ""),
            requested_from=str(requested_from or ""),
            approval_required=bool(approval_required),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_value(cls, value: Any) -> "ChangeManifest":
        if isinstance(value, cls):
            return value

        if hasattr(value, "to_dict") and callable(value.to_dict):
            value = value.to_dict()

        if not isinstance(value, Mapping):
            raise TypeError(
                "ChangeManifest requires a mapping-compatible value."
            )

        payload = dict(value)

        manifest = cls(
            change_id=str(
                payload.get("change_id")
                or uuid.uuid4().hex
            ),
            created_at=str(
                payload.get("created_at")
                or _utc_now()
            ),
            updated_at=str(
                payload.get("updated_at")
                or _utc_now()
            ),
            status=str(payload.get("status") or "generated"),
            project_root=str(payload.get("project_root") or ""),
            title=str(payload.get("title") or ""),
            summary=str(payload.get("summary") or ""),
            finding=dict(payload.get("finding") or {}),
            review=dict(payload.get("review") or {}),
            plan=dict(payload.get("plan") or {}),
            patch=str(payload.get("patch") or ""),
            files=[
                FileChangeRecord.from_value(item)
                for item in (payload.get("files") or [])
            ],
            approval_required=bool(
                payload.get("approval_required", True)
            ),
            approved=bool(payload.get("approved", False)),
            approved_at=str(payload.get("approved_at") or ""),
            rejected_at=str(payload.get("rejected_at") or ""),
            applied_at=str(payload.get("applied_at") or ""),
            verified_at=str(payload.get("verified_at") or ""),
            rolled_back_at=str(
                payload.get("rolled_back_at") or ""
            ),
            verification=dict(
                payload.get("verification") or {}
            ),
            rollback=dict(payload.get("rollback") or {}),
            provider=str(payload.get("provider") or ""),
            model=str(payload.get("model") or ""),
            requested_from=str(
                payload.get("requested_from") or ""
            ),
            error=str(payload.get("error") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )

        return manifest

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def add_file(
        self,
        value: FileChangeRecord | Mapping[str, Any],
    ) -> FileChangeRecord:
        record = FileChangeRecord.from_value(value)

        existing = self.get_file(record.path)
        if existing is not None:
            self.files.remove(existing)

        self.files.append(record)
        self.touch()
        return record

    def get_file(
        self,
        path: str | Path,
    ) -> Optional[FileChangeRecord]:
        target = str(path)

        for record in self.files:
            if record.path == target:
                return record

        return None

    def approve(self) -> None:
        self.approved = True
        self.approved_at = _utc_now()
        self.rejected_at = ""
        self.status = "approved"
        self.error = ""
        self.touch()

    def reject(self, reason: str = "") -> None:
        self.approved = False
        self.rejected_at = _utc_now()
        self.status = "rejected"
        self.error = str(reason or "")
        self.touch()

    def mark_backup_created(self) -> None:
        self.status = "backed_up"
        self.error = ""
        self.touch()

    def mark_apply_started(self) -> None:
        self.status = "applying"
        self.error = ""
        self.touch()

    def mark_applied(self) -> None:
        self.status = "applied"
        self.applied_at = _utc_now()
        self.error = ""

        for record in self.files:
            if record.status in {"pending", "backed_up"}:
                record.status = "applied"

        self.touch()

    def mark_apply_failed(self, error: str) -> None:
        self.status = "apply_failed"
        self.error = str(error or "Patch application failed.")

        for record in self.files:
            if record.status == "applying":
                record.status = "failed"

        self.touch()

    def mark_verified(
        self,
        report: Mapping[str, Any] | Any,
        *,
        passed: Optional[bool] = None,
    ) -> None:
        if hasattr(report, "to_dict") and callable(report.to_dict):
            report = report.to_dict()

        if isinstance(report, Mapping):
            payload = dict(report)
        else:
            payload = {
                "message": str(report),
            }

        if passed is None:
            if "passed" in payload:
                passed = bool(payload["passed"])
            elif "success" in payload:
                passed = bool(payload["success"])
            elif "valid" in payload:
                passed = bool(payload["valid"])
            else:
                passed = False

        payload["passed"] = bool(passed)

        self.verification = _json_safe(payload)
        self.verified_at = _utc_now()
        self.status = (
            "verified"
            if passed
            else "verification_failed"
        )
        self.error = (
            ""
            if passed
            else str(
                payload.get("message")
                or payload.get("summary")
                or "Verification failed."
            )
        )
        self.touch()

    def mark_rollback_started(self) -> None:
        self.status = "rolling_back"
        self.error = ""
        self.touch()

    def mark_rolled_back(
        self,
        result: Mapping[str, Any] | Any = None,
    ) -> None:
        if hasattr(result, "to_dict") and callable(result.to_dict):
            result = result.to_dict()

        if isinstance(result, Mapping):
            self.rollback = _json_safe(dict(result))
        elif result is not None:
            self.rollback = {
                "message": str(result),
            }

        self.rollback["success"] = True
        self.status = "rolled_back"
        self.rolled_back_at = _utc_now()
        self.error = ""

        for record in self.files:
            record.status = "rolled_back"

        self.touch()

    def mark_rollback_failed(self, error: str) -> None:
        self.rollback = {
            **dict(self.rollback or {}),
            "success": False,
            "error": str(error or "Rollback failed."),
        }
        self.status = "rollback_failed"
        self.error = str(error or "Rollback failed.")
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["files"] = [
            record.to_dict()
            for record in self.files
        ]
        return _json_safe(payload)

    def to_json(
        self,
        *,
        indent: int = 2,
    ) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
            sort_keys=False,
        )

    def save(
        self,
        path: str | Path,
    ) -> Path:
        target = Path(path)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.touch()

        temp = target.with_suffix(
            target.suffix + ".tmp"
        )
        temp.write_text(
            self.to_json(),
            encoding="utf-8",
        )
        temp.replace(target)

        return target

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "ChangeManifest":
        source = Path(path)

        if not source.exists():
            raise FileNotFoundError(
                f"Change manifest does not exist: {source}"
            )

        payload = json.loads(
            source.read_text(encoding="utf-8")
        )

        return cls.from_value(payload)

    def default_filename(self) -> str:
        return f"{self.change_id}.json"

    def default_path(
        self,
        history_root: str | Path,
    ) -> Path:
        return (
            Path(history_root)
            / "manifests"
            / self.default_filename()
        )

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.change_id:
            errors.append("change_id is required.")

        if not self.created_at:
            errors.append("created_at is required.")

        if not self.patch.strip():
            errors.append("patch is empty.")

        seen_paths: set[str] = set()

        for record in self.files:
            if not record.path:
                errors.append(
                    "A file record is missing its path."
                )
                continue

            if record.path in seen_paths:
                errors.append(
                    f"Duplicate file record: {record.path}"
                )

            seen_paths.add(record.path)

        if self.approved and not self.approved_at:
            errors.append(
                "approved_at is required when approved is true."
            )

        if self.status == "applied" and not self.applied_at:
            errors.append(
                "applied_at is required for applied manifests."
            )

        if (
            self.status
            in {"verified", "verification_failed"}
            and not self.verified_at
        ):
            errors.append(
                "verified_at is required after verification."
            )

        if (
            self.status == "rolled_back"
            and not self.rolled_back_at
        ):
            errors.append(
                "rolled_back_at is required after rollback."
            )

        return errors

    @property
    def is_valid(self) -> bool:
        return not self.validate()

    @property
    def can_apply(self) -> bool:
        if not self.patch.strip():
            return False

        if self.approval_required and not self.approved:
            return False

        return self.status in {
            "generated",
            "approved",
            "backed_up",
            "apply_failed",
        }

    @property
    def can_rollback(self) -> bool:
        has_backups = any(
            bool(record.backup_path)
            for record in self.files
        )

        return has_backups and self.status in {
            "applied",
            "verified",
            "verification_failed",
            "rollback_failed",
        }


__all__ = [
    "ChangeManifest",
    "FileChangeRecord",
]
