from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .ai_response_validator import AIResponseValidator
from .preview_diff_panel import PreviewDiff


@dataclass(slots=True)
class DiffGenerationRequest:
    """
    Immutable-style request object used internally by DiffGenerator.
    """

    finding: dict[str, Any]
    review: dict[str, Any]
    plan: dict[str, Any]
    context: dict[str, Any]


class DiffGenerator:
    """
    Generate a safe PreviewDiff without writing to disk.

    Provider output is validated before normalization. The resulting unified
    diff is validated again before it can leave this class.
    """

    def __init__(
        self,
        project_root: str | Path | None = None,
        provider: Any = None,
        encoding: str = "utf-8",
        validator: Optional[AIResponseValidator] = None,
    ) -> None:
        self.project_root = (
            Path(project_root).expanduser().resolve()
            if project_root
            else None
        )
        self.provider = provider
        self.encoding = str(encoding or "utf-8")
        self.validator = validator or AIResponseValidator()
        self._cancelled = False

    def generate(
        self,
        finding: Mapping[str, Any],
        review: Optional[Mapping[str, Any]] = None,
        plan: Optional[Mapping[str, Any]] = None,
        context: Optional[Mapping[str, Any]] = None,
        progress_callback: Optional[
            Callable[[int, str], None]
        ] = None,
    ) -> PreviewDiff:
        self._cancelled = False

        request = DiffGenerationRequest(
            finding=dict(finding or {}),
            review=dict(review or {}),
            plan=dict(plan or {}),
            context=dict(context or {}),
        )

        self._progress(progress_callback, 5, "Resolving target file...")
        file_path = self._resolve_target_path(request)
        display_path = self._display_path(file_path, request)
        self._check_cancelled()

        self._progress(progress_callback, 15, "Loading current file content...")
        original_content = self._resolve_original_content(request, file_path)
        self._check_cancelled()

        self._progress(progress_callback, 30, "Resolving proposed changes...")
        
        generated = self._generate_candidate(
            request=request,
            file_path=file_path,
            original_content=original_content,
            progress_callback=progress_callback,
        )

        print("\n========== GENERATED CANDIDATE DEBUG ==========")
        print("TYPE:", type(generated))
        print("REPR:", repr(generated))

        if isinstance(generated, str):
            print("LINES:", len(generated.splitlines()))
            print("CHARS:", len(generated))
            print("START:", repr(generated[:500]))

        elif isinstance(generated, Mapping):
            print("KEYS:", list(generated.keys()))
            for key, value in generated.items():
                print(
                    f"{key}:",
                    "type=",
                    type(value),
                    "repr=",
                    repr(value)[:500],
                )
       
        self._raise_if_provider_error(generated)
        self._check_cancelled()

        self._progress(progress_callback, 65, "Cleaning generated response...")
        generated = self.validator.normalise_provider_output(generated)

        self._progress(progress_callback, 70, "Validating AI response...")
        provider_validation = self.validator.validate_provider_output(
            generated,
            original_content=original_content,
            file_path=file_path or display_path,
        )
        provider_validation.raise_for_errors(
            "Generated response blocked"
        )

        preview = self._normalise_candidate(
            generated=generated,
            request=request,
            file_path=file_path,
            display_path=display_path,
            original_content=original_content,
        )

        self._progress(progress_callback, 90, "Validating generated patch...")
        self._validate_preview(
            preview,
            original_content=original_content,
            file_path=file_path or display_path,
        )

        if provider_validation.warnings:
            warning_text = "; ".join(
                item.message
                for item in provider_validation.warnings
            )
            preview.validation_state = "warning"
            preview.validation_message = warning_text

        self._progress(progress_callback, 100, "Diff generation complete")
        return preview
        
    @staticmethod
    def _raise_if_provider_error(value: Any) -> None:
        """
        Reject provider status/error messages before they are treated as
        replacement source code.
        """
        if not isinstance(value, str):
            return

        text = value.strip()
        if not text:
            raise RuntimeError("The AI provider returned an empty response.")

        lower = text.lower()

        error_markers = (
            "ollama is not available:",
            "openrouter is not available:",
            "lm studio is not available:",
            "provider is not available:",
            "connection refused",
            "connection aborted",
            "connection error",
            "read timed out",
            "connect timeout",
            "httpconnectionpool(",
            "httpsconnectionpool(",
            "failed to connect",
            "request failed:",
            "provider error:",
        )

        if any(marker in lower for marker in error_markers):
            raise RuntimeError(text)    

    def generate_diff(self, finding, review=None, plan=None, context=None, progress_callback=None):
        return self.generate(
            finding=finding,
            review=review,
            plan=plan,
            context=context,
            progress_callback=progress_callback,
        )

    def create_preview(self, finding, review=None, plan=None, context=None, progress_callback=None):
        return self.generate(
            finding=finding,
            review=review,
            plan=plan,
            context=context,
            progress_callback=progress_callback,
        )

    def build_preview(self, finding, review=None, plan=None, context=None, progress_callback=None):
        return self.generate(
            finding=finding,
            review=review,
            plan=plan,
            context=context,
            progress_callback=progress_callback,
        )

    def cancel(self) -> None:
        self._cancelled = True
        cancel = getattr(self.provider, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass

    def _resolve_target_path(self, request: DiffGenerationRequest) -> Optional[Path]:
        raw_path = (
            request.plan.get("file_path")
            or request.plan.get("file")
            or request.finding.get("file_path")
            or request.finding.get("file")
            or request.context.get("file_path")
            or request.context.get("file")
        )
        if not raw_path:
            return None

        candidate = Path(str(raw_path)).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        if self.project_root is not None:
            return (self.project_root / candidate).resolve()
        return candidate.resolve()

    def _resolve_original_content(
        self,
        request: DiffGenerationRequest,
        file_path: Optional[Path],
    ) -> str:
        for mapping in (request.context, request.plan):
            inline = self._first_text(
                mapping,
                ("original_content", "current_content", "source_content"),
            )
            if inline is not None:
                return inline

        if file_path is None or not file_path.exists():
            return ""
        if not file_path.is_file():
            raise RuntimeError(f"Diff target is not a file: {file_path}")

        return file_path.read_text(
            encoding=self.encoding,
            errors="replace",
        )

    def _generate_candidate(
        self,
        request: DiffGenerationRequest,
        file_path: Optional[Path],
        original_content: str,
        progress_callback: Optional[Callable[[int, str], None]],
    ) -> Any:
        ready_patch = self._extract_ready_patch(request)
        if ready_patch:
            return {
                "patch": ready_patch,
                "file_path": self._display_path(file_path, request),
                "summary": self._build_summary(request),
                "validation_state": "pending",
            }

        proposed_content = self._extract_proposed_content(request)
        if proposed_content is not None:
            return {
                "original_content": original_content,
                "proposed_content": proposed_content,
            }

        if self.provider is None:
            raise RuntimeError(
                "No proposed content or patch was supplied, and no "
                "generation provider is configured."
            )

        self._progress(
            progress_callback,
            50,
            "Requesting generated replacement content...",
        )
        return self._invoke_provider(
            provider=self.provider,
            request=request,
            file_path=file_path,
            original_content=original_content,
        )

    def _invoke_provider(
        self,
        provider: Any,
        request: DiffGenerationRequest,
        file_path: Optional[Path],
        original_content: str,
    ) -> Any:
        method = self._resolve_provider_method(provider)

        payload = {
            "finding": dict(request.finding),
            "review": dict(request.review),
            "plan": dict(request.plan),
            "context": dict(request.context),
            "file_path": str(file_path) if file_path is not None else "",
            "original_content": original_content,
        }

        attempts = (
            lambda: method(**payload),
            lambda: method(payload),
            lambda: method(
                request.finding,
                request.review,
                request.plan,
                request.context,
            ),
            lambda: method(
                request.finding,
                request.review,
                request.plan,
            ),
            lambda: method(original_content, request.plan),
            lambda: method(original_content),
            lambda: method(),
        )

        last_type_error: Optional[TypeError] = None
        for attempt in attempts:
            try:
                return attempt()
            except TypeError as exc:
                last_type_error = exc

        if last_type_error is not None:
            raise last_type_error
        raise RuntimeError("Could not invoke the configured diff provider.")

    def _resolve_provider_method(self, provider: Any):
        if callable(provider):
            return provider

        for name in (
            "generate_diff",
            "generate_preview",
            "generate_patch",
            "generate",
            "complete",
            "run",
        ):
            method = getattr(provider, name, None)
            if callable(method):
                return method

        raise RuntimeError(
            "The configured provider does not expose a supported "
            "generation method."
        )

    def _normalise_candidate(
        self,
        generated: Any,
        request: DiffGenerationRequest,
        file_path: Optional[Path],
        display_path: str,
        original_content: str,
    ) -> PreviewDiff:
        if isinstance(generated, PreviewDiff):
            preview = generated
        elif hasattr(generated, "to_dict") and callable(generated.to_dict):
            preview = PreviewDiff.from_value(generated.to_dict())
        elif isinstance(generated, str):
            if self._looks_like_patch(generated):
                preview = PreviewDiff(patch=generated)
            else:
                preview = self._preview_from_contents(
                    original_content=original_content,
                    proposed_content=generated,
                    display_path=display_path,
                )
        elif isinstance(generated, Mapping):
            generated_map = dict(generated)
            patch = self._first_text(
                generated_map,
                ("patch", "diff", "unified_diff", "preview"),
            )
            if patch:
                preview = PreviewDiff.from_value(generated_map)
            else:
                proposed_content = self._first_text(
                    generated_map,
                    (
                        "proposed_content",
                        "replacement_content",
                        "updated_content",
                        "new_content",
                        "content",
                    ),
                )
                if proposed_content is None:
                    raise RuntimeError(
                        "The diff provider returned no patch and no "
                        "replacement content."
                    )

                original = self._first_text(
                    generated_map,
                    ("original_content", "current_content"),
                )
                preview = self._preview_from_contents(
                    original_content=(
                        original if original is not None else original_content
                    ),
                    proposed_content=proposed_content,
                    display_path=str(
                        generated_map.get("file_path")
                        or generated_map.get("file")
                        or display_path
                    ),
                )
                preview.title = str(
                    generated_map.get("title") or preview.title
                )
                preview.summary = str(
                    generated_map.get("summary")
                    or generated_map.get("description")
                    or ""
                )
                preview.validation_state = str(
                    generated_map.get("validation_state", "pending")
                )
                preview.validation_message = str(
                    generated_map.get("validation_message", "")
                )
                preview.metadata.update(
                    dict(generated_map.get("metadata") or {})
                )
        else:
            raise RuntimeError(
                "The diff provider returned an unsupported result type: "
                f"{type(generated).__name__}"
            )

        if not preview.file_path:
            preview.file_path = display_path
        if not preview.title or preview.title == "Generated Patch":
            preview.title = self._build_title(request)
        if not preview.summary:
            preview.summary = self._build_summary(request)

        preview.metadata = {
            **dict(preview.metadata or {}),
            "finding": dict(request.finding),
            "review": dict(request.review),
            "plan": dict(request.plan),
            "context": dict(request.context),
            "target_path": str(file_path) if file_path is not None else "",
            "generator": type(self).__name__,
            "ai_validation": "passed",
        }
        return preview

    def _preview_from_contents(
        self,
        original_content: str,
        proposed_content: str,
        display_path: str,
    ) -> PreviewDiff:
        path = display_path or "generated_file"
        original_lines = original_content.splitlines(keepends=True)
        proposed_lines = proposed_content.splitlines(keepends=True)

        patch_lines = difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
        patch = "\n".join(patch_lines)

        return PreviewDiff(
            patch=patch,
            file_path=path,
            title=f"Preview: {Path(path).name}",
            validation_state="pending",
        )

    def _extract_ready_patch(self, request: DiffGenerationRequest) -> Optional[str]:
        for mapping in (
            request.context,
            request.plan,
            request.review,
            request.finding,
        ):
            value = self._first_text(
                mapping,
                ("patch", "diff", "unified_diff", "preview_diff"),
            )
            if value:
                return value
        return None

    def _extract_proposed_content(self, request: DiffGenerationRequest) -> Optional[str]:
        for mapping in (
            request.context,
            request.plan,
            request.review,
            request.finding,
        ):
            value = self._first_text(
                mapping,
                (
                    "proposed_content",
                    "replacement_content",
                    "updated_content",
                    "new_content",
                    "fixed_content",
                ),
            )
            if value is not None:
                return value
        return None

    def _display_path(
        self,
        file_path: Optional[Path],
        request: DiffGenerationRequest,
    ) -> str:
        raw = (
            request.plan.get("file_path")
            or request.plan.get("file")
            or request.finding.get("file_path")
            or request.finding.get("file")
            or request.context.get("file_path")
            or request.context.get("file")
            or ""
        )
        if raw:
            return str(raw).replace("\\", "/")
        if file_path is None:
            return ""

        if self.project_root is not None:
            try:
                return str(
                    file_path.relative_to(self.project_root)
                ).replace("\\", "/")
            except ValueError:
                pass
        return str(file_path).replace("\\", "/")

    def _build_title(self, request: DiffGenerationRequest) -> str:
        title = str(
            request.finding.get("title")
            or request.finding.get("description")
            or request.plan.get("title")
            or "Generated Patch"
        ).strip()
        return f"Preview: {title}" if title else "Generated Patch"

    def _build_summary(self, request: DiffGenerationRequest) -> str:
        return str(
            request.plan.get("summary")
            or request.plan.get("objective")
            or request.plan.get("description")
            or request.review.get("recommended_repair")
            or request.review.get("suggested_fix")
            or request.review.get("summary")
            or request.finding.get("suggested_request")
            or ""
        ).strip()

    def _validate_preview(
        self,
        preview: PreviewDiff,
        *,
        original_content: str,
        file_path: str | Path | None,
    ) -> None:
        patch = preview.patch.strip()
        if not patch:
            raise RuntimeError("Diff generation produced an empty patch.")
        if not self._looks_like_patch(patch):
            raise RuntimeError("Generated output is not a valid unified diff.")

        validation = self.validator.validate_preview_patch(
            preview.patch,
            original_content=original_content,
            file_path=file_path,
        )
        validation.raise_for_errors("Generated patch blocked")

        additions, deletions = PreviewDiff.count_changes(preview.patch)
        changed_files = PreviewDiff.count_files(preview.patch)
        preview.additions = additions
        preview.deletions = deletions
        preview.changed_files = changed_files

        if validation.warnings:
            preview.validation_state = "warning"
            preview.validation_message = "; ".join(
                item.message
                for item in validation.warnings
            )
        elif preview.validation_state in {"", "unknown", "pending"}:
            preview.validation_state = "passed"
            preview.validation_message = "AI response and patch validation passed."

        preview.metadata = {
            **dict(preview.metadata or {}),
            "validation": validation.to_dict(),
        }

    def _check_cancelled(self) -> None:
        if self._cancelled:
            raise RuntimeError("Diff generation was cancelled.")

    @staticmethod
    def _progress(callback, value: int, message: str) -> None:
        if callback is None:
            return
        try:
            callback(int(value), str(message))
        except Exception:
            pass

    @staticmethod
    def _looks_like_patch(value: str) -> bool:
        return AIResponseValidator.looks_like_patch(value)

    @staticmethod
    def _first_text(
        mapping: Mapping[str, Any],
        keys: Sequence[str],
    ) -> Optional[str]:
        for key in keys:
            if key not in mapping:
                continue
            value = mapping.get(key)
            if value is None:
                continue
            return value if isinstance(value, str) else str(value)
        return None


__all__ = [
    "DiffGenerationRequest",
    "DiffGenerator",
]
