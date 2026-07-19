from __future__ import annotations

from typing import Any, Mapping, Optional

from PySide6.QtCore import QObject, Signal, Slot

from .preview_diff_panel import PreviewDiff


class PreviewDiffWorker(QObject):
    """
    Background worker that generates a PreviewDiff without blocking the UI.

    The worker is intentionally backend-agnostic. It accepts any generator
    object exposing one of these methods:

        generate(...)
        generate_diff(...)
        create_preview(...)
        build_preview(...)

    The generator may return:

        PreviewDiff
        dict
        object exposing to_dict()
        raw unified-diff string

    The result is normalised into PreviewDiff before being emitted.
    """

    started = Signal()
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        generator: Any,
        finding: Mapping[str, Any],
        review: Optional[Mapping[str, Any]] = None,
        plan: Optional[Mapping[str, Any]] = None,
        context: Optional[Mapping[str, Any]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.generator = generator
        self.finding = dict(finding or {})
        self.review = dict(review or {})
        self.plan = dict(plan or {})
        self.context = dict(context or {})

        self._cancelled = False

    @Slot()
    def run(self) -> None:
        if self._cancelled:
            self.failed.emit("Preview generation was cancelled.")
            return

        self.started.emit()
        self.progress.emit(5, "Preparing preview generation...")

        try:
            if self.generator is None:
                raise RuntimeError(
                    "Preview generation is unavailable because no "
                    "DiffGenerator was provided."
                )

            method = self._resolve_generator_method()

            if self._cancelled:
                self.failed.emit("Preview generation was cancelled.")
                return

            self.progress.emit(20, "Generating code changes...")

            result = self._invoke_generator(method)

            if self._cancelled:
                self.failed.emit("Preview generation was cancelled.")
                return

            self.progress.emit(85, "Normalising generated patch...")

            preview = self._normalise_result(result)

            if not preview.patch.strip():
                raise RuntimeError(
                    "The diff generator completed without producing a patch."
                )

            self.progress.emit(100, "Preview ready")
            self.finished.emit(preview)

        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        """
        Request cooperative cancellation.

        This cannot forcibly interrupt a provider call already running, but it
        prevents subsequent work and suppresses successful completion.
        """
        self._cancelled = True

        cancel = getattr(self.generator, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass

    def _resolve_generator_method(self):
        for name in (
            "generate",
            "generate_diff",
            "create_preview",
            "build_preview",
        ):
            method = getattr(self.generator, name, None)
            if callable(method):
                return method

        raise RuntimeError(
            "DiffGenerator does not expose generate(), generate_diff(), "
            "create_preview(), or build_preview()."
        )

    def _invoke_generator(self, method):
        """
        Call the generator using progressively simpler signatures.

        This keeps the worker compatible with early and later DiffGenerator
        implementations while the backend evolves.
        """
        attempts = (
            lambda: method(
                finding=self.finding,
                review=self.review,
                plan=self.plan,
                context=self.context,
                progress_callback=self._on_generator_progress,
            ),
            lambda: method(
                finding=self.finding,
                review=self.review,
                plan=self.plan,
                context=self.context,
            ),
            lambda: method(
                finding=self.finding,
                review=self.review,
                plan=self.plan,
            ),
            lambda: method(
                self.finding,
                self.review,
                self.plan,
                self.context,
            ),
            lambda: method(
                self.finding,
                self.review,
                self.plan,
            ),
            lambda: method(
                self.finding,
                self.plan,
            ),
            lambda: method(self.plan),
            lambda: method(),
        )

        last_type_error: Optional[TypeError] = None

        for attempt in attempts:
            try:
                return attempt()
            except TypeError as exc:
                last_type_error = exc
                continue

        if last_type_error is not None:
            raise last_type_error

        raise RuntimeError("Could not invoke the diff generator.")

    def _normalise_result(self, result: Any) -> PreviewDiff:
        if isinstance(result, PreviewDiff):
            preview = result

        elif hasattr(result, "to_dict") and callable(result.to_dict):
            preview = PreviewDiff.from_value(result.to_dict())

        elif isinstance(result, (dict, str)):
            preview = PreviewDiff.from_value(result)

        else:
            preview = PreviewDiff.from_value(result)

        if not preview.file_path:
            preview.file_path = str(
                self.finding.get("file")
                or self.plan.get("file")
                or self.plan.get("file_path")
                or ""
            )

        if preview.title == "Generated Patch":
            finding_title = str(
                self.finding.get("title")
                or self.finding.get("description")
                or ""
            ).strip()

            if finding_title:
                preview.title = f"Preview: {finding_title}"

        if not preview.summary:
            preview.summary = str(
                self.plan.get("summary")
                or self.plan.get("objective")
                or self.review.get("recommended_repair")
                or self.review.get("summary")
                or ""
            )

        if not preview.validation_state:
            preview.validation_state = "pending"

        preview.metadata = {
            **dict(preview.metadata or {}),
            "finding": dict(self.finding),
            "review": dict(self.review),
            "plan": dict(self.plan),
            "context": dict(self.context),
        }

        return preview

    def _on_generator_progress(
        self,
        value: Any,
        message: str = "",
    ) -> None:
        if self._cancelled:
            return

        try:
            percent = int(value)
        except (TypeError, ValueError):
            percent = 0

        percent = max(20, min(80, percent))
        self.progress.emit(
            percent,
            str(message or "Generating code changes..."),
        )


__all__ = [
    "PreviewDiffWorker",
]
