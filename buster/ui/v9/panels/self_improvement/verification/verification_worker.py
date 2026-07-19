
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PySide6.QtCore import QObject, QRunnable, Signal

from .verification_engine import VerificationEngine
from .verification_report import VerificationReport


class VerificationWorkerSignals(QObject):
    started = Signal()
    progress = Signal(str)
    finished = Signal(object)   # VerificationReport
    failed = Signal(str)


class VerificationWorker(QRunnable):
    """
    Background worker for VerificationEngine.

    Submit to a QThreadPool:
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        project_root: str | Path,
        files: Iterable[str | Path],
        *,
        launch_command: Sequence[str] | None = None,
        change_id: str = "",
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)

        self.project_root = Path(project_root)
        self.files = list(files)
        self.launch_command = list(launch_command) if launch_command else None
        self.change_id = change_id
        self.signals = VerificationWorkerSignals()

    def run(self) -> None:
        try:
            self.signals.started.emit()
            self.signals.progress.emit("Starting verification...")

            engine = VerificationEngine(self.project_root)

            self.signals.progress.emit("Running verification checks...")

            report: VerificationReport = engine.verify(
                self.files,
                launch_command=self.launch_command,
                change_id=self.change_id,
            )

            self.signals.progress.emit(report.summary)
            self.signals.finished.emit(report)

        except Exception as exc:
            self.signals.failed.emit(str(exc))


__all__ = [
    "VerificationWorker",
    "VerificationWorkerSignals",
]
