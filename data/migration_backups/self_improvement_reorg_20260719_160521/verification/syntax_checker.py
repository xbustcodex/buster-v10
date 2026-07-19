from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import Any, Iterable, Optional

from .verification_report import (
    CheckResult,
    CheckStatus,
    VerificationIssue,
)


class SyntaxChecker:
    """
    Validate Python source syntax without importing or executing code.
    """

    name = "syntax"

    def __init__(
        self,
        project_root: str | Path,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

    def check(
        self,
        files: Iterable[str | Path],
        *,
        required: bool = True,
    ) -> CheckResult:
        started = time.perf_counter()

        result = CheckResult(
            name=self.name,
            status=CheckStatus.RUNNING,
            passed=False,
            required=required,
            summary="Checking Python syntax...",
        )
        result.start()

        targets = self._resolve_files(files)

        if not targets:
            duration = time.perf_counter() - started
            return CheckResult.skipped_result(
                self.name,
                "No Python files were available for syntax checking.",
                required=False,
                duration_seconds=duration,
                metadata={
                    "checked_files": 0,
                    "skipped_files": 0,
                },
            )

        checked = 0
        skipped = 0

        for path in targets:
            if path.suffix.lower() != ".py":
                skipped += 1
                continue

            checked += 1
            self._check_file(path, result)

        duration = time.perf_counter() - started
        result.duration_seconds = duration

        if checked == 0:
            result.finish(
                CheckStatus.SKIPPED,
                "No Python files were available for syntax checking.",
            )
            result.required = False
            result.passed = True
        elif result.issues:
            result.finish(
                CheckStatus.FAILED,
                (
                    f"Syntax validation failed with "
                    f"{len(result.issues)} issue(s)."
                ),
            )
        else:
            result.finish(
                CheckStatus.PASSED,
                f"Syntax validation passed for {checked} file(s).",
            )

        result.metadata.update(
            {
                "checked_files": checked,
                "skipped_files": skipped,
                "target_count": len(targets),
            }
        )

        return result

    def check_file(
        self,
        file_path: str | Path,
        *,
        required: bool = True,
    ) -> CheckResult:
        return self.check(
            [file_path],
            required=required,
        )

    def _check_file(
        self,
        path: Path,
        result: CheckResult,
    ) -> None:
        if not path.exists():
            result.add_issue(
                VerificationIssue(
                    message="File does not exist.",
                    severity="error",
                    file=str(path),
                    checker=self.name,
                    code="FILE_NOT_FOUND",
                )
            )
            return

        if not path.is_file():
            result.add_issue(
                VerificationIssue(
                    message="Target is not a file.",
                    severity="error",
                    file=str(path),
                    checker=self.name,
                    code="NOT_A_FILE",
                )
            )
            return

        try:
            source = path.read_text(
                encoding="utf-8",
            )
        except UnicodeDecodeError:
            try:
                source = path.read_text(
                    encoding="utf-8-sig",
                )
            except Exception as exc:
                result.add_issue(
                    VerificationIssue(
                        message="Could not decode Python source.",
                        severity="error",
                        file=str(path),
                        checker=self.name,
                        code="DECODE_ERROR",
                        details=str(exc),
                    )
                )
                return
        except Exception as exc:
            result.add_issue(
                VerificationIssue(
                    message="Could not read Python source.",
                    severity="error",
                    file=str(path),
                    checker=self.name,
                    code="READ_ERROR",
                    details=str(exc),
                )
            )
            return

        try:
            ast.parse(
                source,
                filename=str(path),
                mode="exec",
                type_comments=True,
            )
        except SyntaxError as exc:
            line_text = (exc.text or "").rstrip()

            result.add_issue(
                VerificationIssue(
                    message=str(exc.msg or "Invalid Python syntax."),
                    severity="error",
                    file=str(path),
                    line=int(exc.lineno or 0),
                    column=int(exc.offset or 0),
                    checker=self.name,
                    code="SYNTAX_ERROR",
                    details=line_text,
                    metadata={
                        "end_line": int(
                            getattr(exc, "end_lineno", 0) or 0
                        ),
                        "end_column": int(
                            getattr(exc, "end_offset", 0) or 0
                        ),
                    },
                )
            )
        except Exception as exc:
            result.add_issue(
                VerificationIssue(
                    message="Unexpected syntax checker error.",
                    severity="error",
                    file=str(path),
                    checker=self.name,
                    code="CHECKER_ERROR",
                    details=str(exc),
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


__all__ = [
    "SyntaxChecker",
]
