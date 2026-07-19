from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, Enum):
        return value.value

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


class CheckStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"
    ERROR = "error"
    CANCELLED = "cancelled"

    @property
    def is_success(self) -> bool:
        return self in {
            CheckStatus.PASSED,
            CheckStatus.SKIPPED,
            CheckStatus.WARNING,
        }

    @property
    def is_terminal(self) -> bool:
        return self not in {
            CheckStatus.PENDING,
            CheckStatus.RUNNING,
        }


@dataclass(slots=True)
class VerificationIssue:
    message: str
    severity: str = "error"
    file: str = ""
    line: int = 0
    column: int = 0
    code: str = ""
    checker: str = ""
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "VerificationIssue":
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            return cls(message=value)

        if hasattr(value, "to_dict") and callable(value.to_dict):
            value = value.to_dict()

        if not isinstance(value, Mapping):
            return cls(message=str(value))

        payload = dict(value)

        return cls(
            message=str(payload.get("message") or ""),
            severity=str(payload.get("severity") or "error"),
            file=str(payload.get("file") or ""),
            line=int(payload.get("line") or 0),
            column=int(payload.get("column") or 0),
            code=str(payload.get("code") or ""),
            checker=str(payload.get("checker") or ""),
            details=str(payload.get("details") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(slots=True)
class CheckResult:
    name: str
    status: CheckStatus = CheckStatus.PENDING
    passed: bool = False
    required: bool = True
    summary: str = ""
    details: str = ""
    command: str = ""
    duration_seconds: float = 0.0
    started_at: str = ""
    completed_at: str = ""
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    issues: list[VerificationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "CheckResult":
        if isinstance(value, cls):
            return value

        if hasattr(value, "to_dict") and callable(value.to_dict):
            value = value.to_dict()

        if not isinstance(value, Mapping):
            raise TypeError(
                "CheckResult requires a mapping-compatible value."
            )

        payload = dict(value)
        raw_status = payload.get("status") or CheckStatus.PENDING.value

        try:
            status = CheckStatus(str(raw_status))
        except ValueError:
            status = CheckStatus.ERROR

        passed = bool(
            payload.get("passed")
            if "passed" in payload
            else status.is_success
        )

        return cls(
            name=str(payload.get("name") or ""),
            status=status,
            passed=passed,
            required=bool(payload.get("required", True)),
            summary=str(payload.get("summary") or ""),
            details=str(payload.get("details") or ""),
            command=str(payload.get("command") or ""),
            duration_seconds=float(
                payload.get("duration_seconds") or 0.0
            ),
            started_at=str(payload.get("started_at") or ""),
            completed_at=str(payload.get("completed_at") or ""),
            exit_code=(
                int(payload["exit_code"])
                if payload.get("exit_code") is not None
                else None
            ),
            stdout=str(payload.get("stdout") or ""),
            stderr=str(payload.get("stderr") or ""),
            issues=[
                VerificationIssue.from_value(item)
                for item in (payload.get("issues") or [])
            ],
            metadata=dict(payload.get("metadata") or {}),
        )

    @classmethod
    def passed_result(
        cls,
        name: str,
        summary: str = "",
        *,
        required: bool = True,
        **kwargs: Any,
    ) -> "CheckResult":
        return cls(
            name=name,
            status=CheckStatus.PASSED,
            passed=True,
            required=required,
            summary=summary or f"{name} passed.",
            completed_at=_utc_now(),
            **kwargs,
        )

    @classmethod
    def failed_result(
        cls,
        name: str,
        summary: str,
        *,
        issues: Optional[Iterable[Any]] = None,
        required: bool = True,
        status: CheckStatus = CheckStatus.FAILED,
        **kwargs: Any,
    ) -> "CheckResult":
        return cls(
            name=name,
            status=status,
            passed=False,
            required=required,
            summary=summary,
            completed_at=_utc_now(),
            issues=[
                VerificationIssue.from_value(item)
                for item in (issues or [])
            ],
            **kwargs,
        )

    @classmethod
    def skipped_result(
        cls,
        name: str,
        summary: str,
        *,
        required: bool = False,
        **kwargs: Any,
    ) -> "CheckResult":
        return cls(
            name=name,
            status=CheckStatus.SKIPPED,
            passed=True,
            required=required,
            summary=summary,
            completed_at=_utc_now(),
            **kwargs,
        )

    def start(self) -> None:
        self.status = CheckStatus.RUNNING
        self.passed = False
        self.started_at = _utc_now()
        self.completed_at = ""

    def finish(
        self,
        status: CheckStatus,
        summary: str = "",
    ) -> None:
        self.status = status
        self.passed = status.is_success
        self.summary = summary or self.summary
        self.completed_at = _utc_now()

    def add_issue(
        self,
        issue: VerificationIssue | Mapping[str, Any] | str,
    ) -> VerificationIssue:
        item = VerificationIssue.from_value(issue)
        self.issues.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["issues"] = [
            issue.to_dict()
            for issue in self.issues
        ]
        return _json_safe(payload)


@dataclass(slots=True)
class VerificationReport:
    report_id: str
    change_id: str = ""
    project_root: str = ""
    target_files: list[str] = field(default_factory=list)
    passed: bool = False
    status: str = "pending"
    summary: str = ""
    started_at: str = field(default_factory=_utc_now)
    completed_at: str = ""
    duration_seconds: float = 0.0
    checks: list[CheckResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        report_id: str,
        *,
        change_id: str = "",
        project_root: str = "",
        target_files: Optional[Iterable[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "VerificationReport":
        return cls(
            report_id=report_id,
            change_id=change_id,
            project_root=project_root,
            target_files=list(target_files or []),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_value(cls, value: Any) -> "VerificationReport":
        if isinstance(value, cls):
            return value

        if hasattr(value, "to_dict") and callable(value.to_dict):
            value = value.to_dict()

        if not isinstance(value, Mapping):
            raise TypeError(
                "VerificationReport requires a mapping-compatible value."
            )

        payload = dict(value)

        return cls(
            report_id=str(payload.get("report_id") or ""),
            change_id=str(payload.get("change_id") or ""),
            project_root=str(payload.get("project_root") or ""),
            target_files=[
                str(item)
                for item in (payload.get("target_files") or [])
            ],
            passed=bool(payload.get("passed", False)),
            status=str(payload.get("status") or "pending"),
            summary=str(payload.get("summary") or ""),
            started_at=str(
                payload.get("started_at")
                or _utc_now()
            ),
            completed_at=str(payload.get("completed_at") or ""),
            duration_seconds=float(
                payload.get("duration_seconds") or 0.0
            ),
            checks=[
                CheckResult.from_value(item)
                for item in (payload.get("checks") or [])
            ],
            metadata=dict(payload.get("metadata") or {}),
        )

    def add_check(
        self,
        check: CheckResult | Mapping[str, Any],
    ) -> CheckResult:
        item = CheckResult.from_value(check)

        existing = self.get_check(item.name)
        if existing is not None:
            self.checks.remove(existing)

        self.checks.append(item)
        self.recalculate()
        return item

    def get_check(self, name: str) -> Optional[CheckResult]:
        lowered = name.strip().lower()

        for check in self.checks:
            if check.name.strip().lower() == lowered:
                return check

        return None

    def recalculate(self) -> None:
        if not self.checks:
            self.passed = False
            self.status = "pending"
            self.summary = "No verification checks have run."
            return

        required_checks = [
            check
            for check in self.checks
            if check.required
        ]

        terminal = all(
            check.status.is_terminal
            for check in self.checks
        )

        required_passed = all(
            check.status.is_success
            for check in required_checks
        )

        has_error = any(
            check.status in {
                CheckStatus.ERROR,
                CheckStatus.CANCELLED,
            }
            for check in self.checks
        )

        has_failure = any(
            check.status == CheckStatus.FAILED
            for check in required_checks
        )

        if not terminal:
            self.passed = False
            self.status = "running"
            self.summary = "Verification is still running."
            return

        self.passed = required_passed and not has_error

        if has_error:
            self.status = "error"
            self.summary = "Verification encountered an error."
        elif has_failure:
            self.status = "failed"
            self.summary = "One or more required checks failed."
        elif self.passed:
            self.status = "passed"
            self.summary = "All required verification checks passed."
        else:
            self.status = "failed"
            self.summary = "Verification did not pass."

    def complete(
        self,
        duration_seconds: float = 0.0,
    ) -> None:
        self.duration_seconds = float(duration_seconds)
        self.completed_at = _utc_now()
        self.recalculate()

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [
            check
            for check in self.checks
            if check.status in {
                CheckStatus.FAILED,
                CheckStatus.ERROR,
                CheckStatus.CANCELLED,
            }
        ]

    @property
    def warnings(self) -> list[CheckResult]:
        return [
            check
            for check in self.checks
            if check.status == CheckStatus.WARNING
        ]

    @property
    def issue_count(self) -> int:
        return sum(
            len(check.issues)
            for check in self.checks
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [
            check.to_dict()
            for check in self.checks
        ]
        payload["issue_count"] = self.issue_count
        payload["failed_check_names"] = [
            check.name
            for check in self.failed_checks
        ]
        return _json_safe(payload)


__all__ = [
    "CheckResult",
    "CheckStatus",
    "VerificationIssue",
    "VerificationReport",
]
