from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Signal, Slot

from .preview_diff_panel import PreviewDiff


class ApplyChangesWorker(QObject):
    """
    Background worker that applies an approved PreviewDiff.

    The worker delegates to an injected applier service. Supported methods:

      apply(preview,...)
      apply_patch(preview,...)
      run(preview,...)

    The worker never decides whether a patch is safe; it assumes the user has
    already approved the PreviewDiff.
    """

    started = Signal()
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        applier: Any,
        preview: PreviewDiff,
        backup: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.applier = applier
        self.preview = preview
        self.backup = backup
        self._cancelled = False
        self._external_progress = progress_callback

    @Slot()
    def run(self):
        self.started.emit()
        self._emit_progress(5, "Preparing changes...")

        try:
            if self.applier is None:
                raise RuntimeError("No patch applier configured.")

            method = self._resolve_method()

            self._emit_progress(25, "Applying patch...")

            result = self._invoke(method)

            if self._cancelled:
                raise RuntimeError("Patch application cancelled.")

            self._emit_progress(100, "Changes applied.")
            self.finished.emit(result)

        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def cancel(self):
        self._cancelled = True
        cancel = getattr(self.applier, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass

    def _resolve_method(self):
        for name in ("apply", "apply_patch", "run"):
            fn = getattr(self.applier, name, None)
            if callable(fn):
                return fn
        if callable(self.applier):
            return self.applier
        raise RuntimeError("Patch applier exposes no supported apply method.")

    def _invoke(self, fn):
        attempts = (
            lambda: fn(
                preview=self.preview,
                backup=self.backup,
                progress_callback=self._emit_progress,
            ),
            lambda: fn(
                self.preview,
                self.backup,
                self._emit_progress,
            ),
            lambda: fn(self.preview, self.backup),
            lambda: fn(self.preview),
            lambda: fn(),
        )

        last = None
        for a in attempts:
            try:
                return a()
            except TypeError as e:
                last = e
        if last:
            raise last

    def _emit_progress(self, value: int, message: str):
        if self._cancelled:
            return
        self.progress.emit(int(value), str(message))
        if self._external_progress:
            try:
                self._external_progress(int(value), str(message))
            except Exception:
                pass


__all__ = ["ApplyChangesWorker"]
