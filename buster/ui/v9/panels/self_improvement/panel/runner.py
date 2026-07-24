from __future__ import annotations

import logging
from typing import Any, Callable
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)


class GenericRunnableWorker(QRunnable):
    def __init__(self, task_fn: Callable[[], Any]) -> None:
        super().__init__()
        self.task_fn = task_fn
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.task_fn()
            self.signals.finished.emit(result)
        except Exception as exc:
            logger.exception("Background runnable task failed")
            self.signals.failed.emit(str(exc))


def run_async_task(
    task_fn: Callable[[], Any],
    on_finished: Callable[[Any], None],
    on_failed: Callable[[str], None],
) -> None:
    worker = GenericRunnableWorker(task_fn)
    worker.signals.finished.connect(on_finished)
    worker.signals.failed.connect(on_failed)
    QThreadPool.globalInstance().start(worker)