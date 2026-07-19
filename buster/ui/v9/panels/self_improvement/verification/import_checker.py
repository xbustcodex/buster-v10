from __future__ import annotations

import ast
import importlib.util
import sys
import sysconfig
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .verification_report import (
    CheckResult,
    CheckStatus,
    VerificationIssue,
)


@dataclass(slots=True)
class ImportReference:
    module: str
    name: str = ""
    level: int = 0
    file: str = ""
    line: int = 0
    column: int = 0

    @property
    def display_name(self) -> str:
        prefix = "." * max(0, self.level)
        suffix = f".{self.name}" if self.name else ""
        return f"{prefix}{self.module}{suffix}"


class ImportChecker:
    """
    Static Python import validation.

    The checker parses source files with ``ast`` and resolves imports without
    importing or executing project modules.
    """

    name = "imports"

    def __init__(
        self,
        project_root: str | Path,
        *,
        treat_missing_third_party_as_warning: bool = True,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.treat_missing_third_party_as_warning = (
            treat_missing_third_party_as_warning
        )
        self._stdlib_modules = self._load_stdlib_modules()

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
            summary="Checking Python imports...",
        )
        result.start()

        targets = self._resolve_files(files)

        if not targets:
            duration = time.perf_counter() - started
            return CheckResult.skipped_result(
                self.name,
                "No Python files were available for import checking.",
                required=False,
                duration_seconds=duration,
                metadata={
                    "checked_files": 0,
                    "imports_checked": 0,
                },
            )

        checked_files = 0
        imports_checked = 0
        skipped_files = 0
        warnings = 0
        errors = 0

        for path in targets:
            if path.suffix.lower() != ".py":
                skipped_files += 1
                continue

            checked_files += 1

            references = self._extract_imports(
                path,
                result,
            )
            imports_checked += len(references)

            for reference in references:
                issue = self._validate_reference(
                    source_file=path,
                    reference=reference,
                )

                if issue is None:
                    continue

                result.add_issue(issue)

                if issue.severity.lower() == "warning":
                    warnings += 1
                else:
                    errors += 1

        duration = time.perf_counter() - started
        result.duration_seconds = duration

        if checked_files == 0:
            result.finish(
                CheckStatus.SKIPPED,
                "No Python files were available for import checking.",
            )
            result.required = False
            result.passed = True
        elif errors:
            result.finish(
                CheckStatus.FAILED,
                (
                    f"Import validation failed with {errors} error(s) "
                    f"and {warnings} warning(s)."
                ),
            )
        elif warnings:
            result.finish(
                CheckStatus.WARNING,
                (
                    f"Import validation completed with "
                    f"{warnings} warning(s)."
                ),
            )
        else:
            result.finish(
                CheckStatus.PASSED,
                (
                    f"Import validation passed for "
                    f"{imports_checked} import(s)."
                ),
            )

        result.metadata.update(
            {
                "checked_files": checked_files,
                "skipped_files": skipped_files,
                "imports_checked": imports_checked,
                "warnings": warnings,
                "errors": errors,
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

    def _extract_imports(
        self,
        path: Path,
        result: CheckResult,
    ) -> list[ImportReference]:
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
            return []

        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                source = path.read_text(encoding="utf-8-sig")
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
                return []
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
            return []

        try:
            tree = ast.parse(
                source,
                filename=str(path),
                mode="exec",
                type_comments=True,
            )
        except SyntaxError as exc:
            result.add_issue(
                VerificationIssue(
                    message=(
                        "Import analysis skipped because the file "
                        "contains invalid Python syntax."
                    ),
                    severity="error",
                    file=str(path),
                    line=int(exc.lineno or 0),
                    column=int(exc.offset or 0),
                    checker=self.name,
                    code="SYNTAX_ERROR",
                    details=str(exc.msg or ""),
                )
            )
            return []

        references: list[ImportReference] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    references.append(
                        ImportReference(
                            module=alias.name,
                            file=str(path),
                            line=int(getattr(node, "lineno", 0) or 0),
                            column=int(getattr(node, "col_offset", 0) or 0),
                        )
                    )

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""

                if not node.names:
                    references.append(
                        ImportReference(
                            module=module,
                            level=int(node.level or 0),
                            file=str(path),
                            line=int(getattr(node, "lineno", 0) or 0),
                            column=int(getattr(node, "col_offset", 0) or 0),
                        )
                    )
                    continue

                for alias in node.names:
                    references.append(
                        ImportReference(
                            module=module,
                            name=alias.name,
                            level=int(node.level or 0),
                            file=str(path),
                            line=int(getattr(node, "lineno", 0) or 0),
                            column=int(getattr(node, "col_offset", 0) or 0),
                        )
                    )

        return references

    def _validate_reference(
        self,
        *,
        source_file: Path,
        reference: ImportReference,
    ) -> Optional[VerificationIssue]:
        if reference.level > 0:
            return self._validate_relative_import(
                source_file=source_file,
                reference=reference,
            )

        module = reference.module.strip()

        if not module:
            return VerificationIssue(
                message="Import statement has no module name.",
                severity="error",
                file=reference.file,
                line=reference.line,
                column=reference.column,
                checker=self.name,
                code="EMPTY_IMPORT",
            )

        top_level = module.split(".", 1)[0]

        if top_level in self._stdlib_modules:
            return None

        if self._local_module_exists(module):
            return None

        if self._external_module_exists(top_level):
            return None

        severity = (
            "warning"
            if self.treat_missing_third_party_as_warning
            else "error"
        )

        return VerificationIssue(
            message=f"Unresolved import: {module}",
            severity=severity,
            file=reference.file,
            line=reference.line,
            column=reference.column,
            checker=self.name,
            code="UNRESOLVED_IMPORT",
            metadata={
                "module": module,
                "classification": "third_party_or_missing",
            },
        )

    def _validate_relative_import(
        self,
        *,
        source_file: Path,
        reference: ImportReference,
    ) -> Optional[VerificationIssue]:
        package_dir = source_file.parent

        for _ in range(max(0, reference.level - 1)):
            package_dir = package_dir.parent

        if reference.module:
            candidate = package_dir.joinpath(
                *reference.module.split(".")
            )

            if self._module_path_exists(candidate):
                return None

            return VerificationIssue(
                message=(
                    "Unresolved relative import: "
                    f"{reference.display_name}"
                ),
                severity="error",
                file=reference.file,
                line=reference.line,
                column=reference.column,
                checker=self.name,
                code="UNRESOLVED_RELATIVE_IMPORT",
                metadata={
                    "module": reference.display_name,
                    "base_directory": str(package_dir),
                },
            )

        if reference.name == "*":
            if package_dir.exists():
                return None

        if reference.name:
            candidate = package_dir / reference.name

            if self._module_path_exists(candidate):
                return None

            package_init = package_dir / "__init__.py"

            if package_init.exists():
                return None

            return VerificationIssue(
                message=(
                    "Unresolved relative import: "
                    f"{reference.display_name}"
                ),
                severity="error",
                file=reference.file,
                line=reference.line,
                column=reference.column,
                checker=self.name,
                code="UNRESOLVED_RELATIVE_IMPORT",
                metadata={
                    "module": reference.display_name,
                    "base_directory": str(package_dir),
                },
            )

        if package_dir.exists():
            return None

        return VerificationIssue(
            message=(
                "Relative import base package does not exist: "
                f"{reference.display_name}"
            ),
            severity="error",
            file=reference.file,
            line=reference.line,
            column=reference.column,
            checker=self.name,
            code="INVALID_RELATIVE_IMPORT",
            metadata={
                "module": reference.display_name,
                "base_directory": str(package_dir),
            },
        )

    def _local_module_exists(self, module: str) -> bool:
        candidate = self.project_root.joinpath(
            *module.split(".")
        )
        return self._module_path_exists(candidate)

    @staticmethod
    def _module_path_exists(candidate: Path) -> bool:
        return (
            candidate.with_suffix(".py").is_file()
            or (
                candidate.is_dir()
                and (candidate / "__init__.py").is_file()
            )
            or candidate.is_file()
        )

    @staticmethod
    def _external_module_exists(module: str) -> bool:
        try:
            return importlib.util.find_spec(module) is not None
        except (
            ImportError,
            AttributeError,
            ModuleNotFoundError,
            ValueError,
        ):
            return False

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
    def _load_stdlib_modules() -> set[str]:
        modules = set(getattr(sys, "stdlib_module_names", set()))

        if modules:
            return modules

        stdlib_path = Path(
            sysconfig.get_paths().get("stdlib", "")
        )

        if stdlib_path.exists():
            for entry in stdlib_path.iterdir():
                if entry.name.startswith("_"):
                    continue

                if entry.is_file() and entry.suffix == ".py":
                    modules.add(entry.stem)
                elif entry.is_dir():
                    modules.add(entry.name)

        return modules


__all__ = [
    "ImportChecker",
    "ImportReference",
]
