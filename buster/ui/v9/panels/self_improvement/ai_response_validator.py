from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [item for item in self.issues if item.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [item for item in self.issues if item.severity == "warning"]

    def raise_for_errors(self, prefix: str = "AI output rejected") -> None:
        if self.valid:
            return
        message = "; ".join(item.message for item in self.errors)
        raise RuntimeError(f"{prefix}: {message or 'Unknown validation failure.'}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [item.to_dict() for item in self.issues],
        }


class AIResponseValidator:
    """
    Validates and safely cleans AI-generated source code and unified diffs.

    Normal Markdown code fences and short explanatory wrappers are removed
    before validation so they do not prevent the Preview panel from opening.
    Obvious refusals, malformed patches, invalid Python, and catastrophic
    replacements remain blocked.
    """

    _REFUSAL_PATTERNS = (
        re.compile(r"^\s*i(?:'m| am)\s+sorry\b", re.IGNORECASE),
        re.compile(r"^\s*i\s+can(?:not|'t)\s+(?:assist|help|comply)\b", re.IGNORECASE),
        re.compile(r"^\s*i\s+won(?:not|'t)\s+(?:assist|help|provide)\b", re.IGNORECASE),
        re.compile(r"^\s*unable\s+to\s+(?:assist|help|comply)\b", re.IGNORECASE),
        re.compile(r"^\s*as\s+an\s+ai\b", re.IGNORECASE),
    )

    _FENCE_RE = re.compile(
        r"```(?:diff|patch|python|py|text)?\s*\n(?P<body>.*?)\n```",
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(
        self,
        *,
        catastrophic_shrink_ratio: float = 0.12,
        minimum_large_file_lines: int = 150,
        max_deletion_ratio: float = 0.95,
    ) -> None:
        self.catastrophic_shrink_ratio = max(
            0.01, min(float(catastrophic_shrink_ratio), 1.0)
        )
        self.minimum_large_file_lines = max(1, int(minimum_large_file_lines))
        self.max_deletion_ratio = max(
            0.01, min(float(max_deletion_ratio), 1.0)
        )

    def normalise_provider_output(self, generated: Any) -> Any:
        """
        Remove harmless Markdown/prose wrappers while preserving result shape.
        """
        if isinstance(generated, str):
            return self._clean_generated_text(generated)

        if isinstance(generated, Mapping):
            result = dict(generated)
            for key in (
                "patch",
                "diff",
                "unified_diff",
                "preview",
                "proposed_content",
                "replacement_content",
                "updated_content",
                "new_content",
                "content",
            ):
                value = result.get(key)
                if isinstance(value, str):
                    result[key] = self._clean_generated_text(value)
            return result

        to_dict = getattr(generated, "to_dict", None)
        if callable(to_dict):
            try:
                return self.normalise_provider_output(to_dict())
            except Exception:
                return generated

        return generated

    def validate_provider_output(
        self,
        generated: Any,
        *,
        original_content: str = "",
        file_path: str | Path | None = None,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        if generated is None:
            return ValidationResult(
                False,
                [ValidationIssue("empty.provider_result", "The provider returned no result.")],
            )

        if isinstance(generated, str):
            issues.extend(self._validate_text(generated))
            if not self.looks_like_patch(generated):
                issues.extend(
                    self._validate_replacement(
                        original_content,
                        generated,
                        file_path,
                    )
                )

        elif isinstance(generated, Mapping):
            data = dict(generated)
            patch = self._first_text(
                data, ("patch", "diff", "unified_diff", "preview")
            )
            proposed = self._first_text(
                data,
                (
                    "proposed_content",
                    "replacement_content",
                    "updated_content",
                    "new_content",
                    "content",
                ),
            )

            if patch:
                issues.extend(self._validate_patch_text(patch))
            elif proposed is not None:
                issues.extend(self._validate_text(proposed))
                issues.extend(
                    self._validate_replacement(
                        original_content,
                        proposed,
                        data.get("file_path") or data.get("file") or file_path,
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        "missing.generated_content",
                        "The provider returned neither a patch nor replacement content.",
                    )
                )

        return ValidationResult(
            not any(item.severity == "error" for item in issues),
            issues,
        )

    def validate_preview_patch(
        self,
        patch: str,
        *,
        original_content: str = "",
        file_path: str | Path | None = None,
    ) -> ValidationResult:
        issues = self._validate_patch_text(patch)
        additions, deletions = self._count_patch_changes(patch)
        original_lines = len(original_content.splitlines())

        if (
            original_lines >= self.minimum_large_file_lines
            and deletions / max(original_lines, 1) >= self.max_deletion_ratio
            and additions < max(5, int(deletions * 0.10))
        ):
            issues.append(
                ValidationIssue(
                    "catastrophic.patch_replacement",
                    "The patch removes nearly the whole file without a comparable replacement.",
                )
            )

        return ValidationResult(
            not any(item.severity == "error" for item in issues),
            issues,
        )

    def _clean_generated_text(self, text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return ""

        # Prefer a fenced diff when one exists.
        fenced = list(self._FENCE_RE.finditer(value))
        for match in fenced:
            body = match.group("body").strip()
            if self.looks_like_patch(body):
                return body

        # Otherwise extract an inline unified diff from surrounding prose.
        lines = value.splitlines()
        start = next(
            (
                index
                for index, line in enumerate(lines)
                if line.startswith("diff --git ") or line.startswith("--- ")
            ),
            None,
        )
        if start is not None:
            candidate = "\n".join(lines[start:]).strip()
            if self.looks_like_patch(candidate):
                return candidate

        # For replacement source, unwrap the first code fence.
        if fenced:
            return fenced[0].group("body").strip()

        return value

    def _validate_text(self, text: str) -> list[ValidationIssue]:
        value = str(text or "").strip()
        if not value:
            return [ValidationIssue("empty.output", "The AI returned empty output.")]

        for pattern in self._REFUSAL_PATTERNS:
            if pattern.search(value[:500]):
                return [
                    ValidationIssue(
                        "ai.refusal",
                        "The AI returned a refusal instead of generated code.",
                    )
                ]
        return []

    def _validate_replacement(
        self,
        original_content: str,
        proposed_content: str,
        file_path: str | Path | None,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        original_lines = len(str(original_content or "").splitlines())
        proposed_lines = len(str(proposed_content or "").splitlines())

        if (
            original_lines >= self.minimum_large_file_lines
            and proposed_lines < max(
                5, int(original_lines * self.catastrophic_shrink_ratio)
            )
        ):
            issues.append(
                ValidationIssue(
                    "catastrophic.replacement",
                    f"Replacement shrinks a {original_lines}-line file to {proposed_lines} lines.",
                )
            )

        if Path(str(file_path or "")).suffix.lower() == ".py":
            try:
                ast.parse(proposed_content or "\n")
            except SyntaxError as exc:
                issues.append(
                    ValidationIssue(
                        "python.syntax",
                        f"Generated Python does not parse: line {exc.lineno}, {exc.msg}.",
                    )
                )
                return issues

            issues.extend(
                self._validate_symbol_survival(
                    str(original_content or ""),
                    str(proposed_content or ""),
                )
            )

        return issues

    def _validate_symbol_survival(
        self,
        original_content: str,
        proposed_content: str,
    ) -> list[ValidationIssue]:
        if not original_content.strip():
            return []

        try:
            old_tree = ast.parse(original_content)
            new_tree = ast.parse(proposed_content or "\n")
        except SyntaxError:
            return []

        old_symbols = self._symbols(old_tree)
        new_symbols = self._symbols(new_tree)

        if len(old_symbols) < 4:
            return []

        missing = sorted(old_symbols - new_symbols)
        if len(missing) / len(old_symbols) < 0.85:
            return []

        return [
            ValidationIssue(
                "python.symbol_loss",
                "The replacement removes most top-level Python symbols: "
                + ", ".join(missing[:6]),
            )
        ]

    def _validate_patch_text(self, patch: str) -> list[ValidationIssue]:
        issues = self._validate_text(patch)
        if issues:
            return issues

        if not self.looks_like_patch(patch):
            issues.append(
                ValidationIssue(
                    "not.patch",
                    "The generated output is not a valid unified diff.",
                )
            )
            return issues

        additions, deletions = self._count_patch_changes(patch)
        if additions == 0 and deletions == 0:
            issues.append(
                ValidationIssue(
                    "patch.no_changes",
                    "The patch contains no changed lines.",
                )
            )

        return issues

    @staticmethod
    def looks_like_patch(value: str) -> bool:
        lines = str(value or "").splitlines()
        return (
            any(line.startswith("--- ") for line in lines)
            and any(line.startswith("+++ ") for line in lines)
            and any(line.startswith("@@") for line in lines)
        )

    @staticmethod
    def _count_patch_changes(patch: str) -> tuple[int, int]:
        additions = 0
        deletions = 0
        for line in str(patch or "").splitlines():
            if line.startswith(("+++", "---")):
                continue
            if line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1
        return additions, deletions

    @staticmethod
    def _symbols(tree: ast.AST) -> set[str]:
        return {
            node.name
            for node in getattr(tree, "body", [])
            if isinstance(
                node,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            )
        }

    @staticmethod
    def _first_text(
        mapping: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> Optional[str]:
        for key in keys:
            value = mapping.get(key)
            if value is not None:
                return value if isinstance(value, str) else str(value)
        return None


__all__ = [
    "AIResponseValidator",
    "ValidationIssue",
    "ValidationResult",
]
