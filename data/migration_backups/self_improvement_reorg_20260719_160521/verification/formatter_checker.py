from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

from .verification_report import (
    CheckResult,
    CheckStatus,
    VerificationIssue,
)


class FormatterChecker:
    """
    Check Python formatting without modifying source files.

    Black is used when available. If Black is not installed, the checker
    returns a structured skipped result rather than failing verification.
    """

    name = "formatting"

    def __init__(
        self,
        project_root: str | Path,
        *,
        timeout_seconds: float = 60.0,
        line_length: Optional[int] = None,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.timeout_seconds = float(timeout_seconds)
        self.line_length = line_length

    def check(
        self,
        files: Iterable[str | Path],
        *,
        required: bool = False,
    ) -> CheckResult:
        started = time.perf_counter()
        targets = [
            path
            for path in self._resolve_files(files)
            if path.suffix.lower() == ".py"
        ]

        if not targets:
            return CheckResult.skipped_result(
                self.name,
                "No Python files were available for formatting checks.",
                required=False,
                duration_seconds=time.perf_counter() - started,
                metadata={
                    "checked_files": 0,
                    "formatter": "",
                },
            )

        command = self._build_black_command(targets)

        if command is None:
            return CheckResult.skipped_result(
                self.name,
                "Black is not installed; formatting check was skipped.",
                required=False,
                duration_seconds=time.perf_counter() - started,
                metadata={
                    "checked_files": 0,
                    "formatter": "black",
                    "available": False,
                },
            )

        result = CheckResult(
            name=self.name,
            status=CheckStatus.RUNNING,
            passed=False,
            required=required,
            summary="Checking Python formatting...",
            command=self._display_command(command),
        )
        result.start()

        try:
            completed = subprocess.run(
                command,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            result.duration_seconds = time.perf_counter() - started
            result.exit_code = None
            result.stdout = self._normalise_output(exc.stdout)
            result.stderr = self._normalise_output(exc.stderr)
            result.add_issue(
                VerificationIssue(
                    message=(
                        "Formatting check exceeded the configured timeout."
                    ),
                    severity="error",
                    checker=self.name,
                    code="FORMATTER_TIMEOUT",
                    details=(
                        f"Timeout: {self.timeout_seconds:.1f} seconds"
                    ),
                )
            )
            result.finish(
                CheckStatus.ERROR,
                "Formatting check timed out.",
            )
            result.metadata.update(
                {
                    "checked_files": len(targets),
                    "formatter": "black",
                    "timeout_seconds": self.timeout_seconds,
                }
            )
            return result
        except OSError as exc:
            result.duration_seconds = time.perf_counter() - started
            result.add_issue(
                VerificationIssue(
                    message="Could not start the formatting checker.",
                    severity="error",
                    checker=self.name,
                    code="FORMATTER_START_ERROR",
                    details=str(exc),
                )
            )
            result.finish(
                CheckStatus.ERROR,
                "Formatting checker could not be started.",
            )
            result.metadata.update(
                {
                    "checked_files": len(targets),
                    "formatter": "black",
                }
            )
            return result

        result.duration_seconds = time.perf_counter() - started
        result.exit_code = completed.returncode
        result.stdout = completed.stdout or ""
        result.stderr = completed.stderr or ""

        if completed.returncode == 0:
            result.finish(
                CheckStatus.PASSED,
                (
                    f"Formatting check passed for "
                    f"{len(targets)} file(s)."
                ),
            )
        elif completed.returncode == 1:
            self._add_black_issues(
                result=result,
                targets=targets,
                output=(
                    (completed.stdout or "")
                    + "\n"
                    + (completed.stderr or "")
                ),
            )
            result.finish(
                CheckStatus.FAILED,
                (
                    f"{len(result.issues) or len(targets)} file(s) "
                    "require formatting."
                ),
            )
        else:
            result.add_issue(
                VerificationIssue(
                    message="Black reported an execution error.",
                    severity="error",
                    checker=self.name,
                    code="FORMATTER_ERROR",
                    details=(
                        (completed.stderr or completed.stdout or "").strip()
                    ),
                )
            )
            result.finish(
                CheckStatus.ERROR,
                "Formatting checker encountered an error.",
            )

        result.metadata.update(
            {
                "checked_files": len(targets),
                "formatter": "black",
                "available": True,
                "line_length": self.line_length,
            }
        )

        return result

    def check_file(
        self,
        file_path: str | Path,
        *,
        required: bool = False,
    ) -> CheckResult:
        return self.check(
            [file_path],
            required=required,
        )

    def _build_black_command(
        self,
        targets: list[Path],
    ) -> Optional[list[str]]:
        executable = shutil.which("black")

        if executable:
            command = [
                executable,
                "--check",
                "--diff",
            ]
        else:
            try:
                import black  # type: ignore  # noqa: F401
            except Exception:
                return None

            command = [
                sys.executable,
                "-m",
                "black",
                "--check",
                "--diff",
            ]

        if self.line_length:
            command.extend(
                [
                    "--line-length",
                    str(self.line_length),
                ]
            )

        command.extend(str(path) for path in targets)
        return command

    def _add_black_issues(
        self,
        *,
        result: CheckResult,
        targets: list[Path],
        output: str,
    ) -> None:
        identified: set[str] = set()

        for line in output.splitlines():
            stripped = line.strip()

            marker = "would reformat "
            if marker not in stripped:
                continue

            path_text = stripped.split(marker, 1)[1].strip()
            path = Path(path_text)

            if not path.is_absolute():
                path = (self.project_root / path).resolve()

            key = str(path).lower()
            if key in identified:
                continue

            identified.add(key)
            result.add_issue(
                VerificationIssue(
                    message="File is not formatted with Black.",
                    severity="error",
                    file=str(path),
                    checker=self.name,
                    code="FORMAT_REQUIRED",
                )
            )

        if result.issues:
            return

        for path in targets:
            result.add_issue(
                VerificationIssue(
                    message="File may require Black formatting.",
                    severity="error",
                    file=str(path),
                    checker=self.name,
                    code="FORMAT_REQUIRED",
                )
            )

    def _resolve_files(
        self,
        files: Iterable[str | Path],
    ) -> list[Path]:
        resolved: list[Path] = []
        seen: set[str] = set()

        for value in files:
            path = Path(value).expanduser()

            if not path.is_absolute():
                path = self.project_root / path

            path = path.resolve()
            key = str(path).lower()

            if key in seen:
                continue

            seen.add(key)
            resolved.append(path)

        return resolved

    @staticmethod
    def _display_command(command: list[str]) -> str:
        return subprocess.list2cmdline(command)

    @staticmethod
    def _normalise_output(value: object) -> str:
        if value is None:
            return ""

        if isinstance(value, bytes):
            return value.decode(
                "utf-8",
                errors="replace",
            )

        return str(value)


__all__ = [
    "FormatterChecker",
]
