from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtCore import QObject, Signal, Slot

from buster.autonomy.code_review_service import CodeReviewService


class CodeReviewWorker(QObject):
    """
    Runs an AI code review away from the Qt GUI thread.
    """

    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: CodeReviewService,
        finding: Mapping[str, Any],
    ) -> None:
        super().__init__()
        self.service = service
        self.finding = dict(finding)

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(
                self.service.review(self.finding)
            )
        except Exception as exc:
            self.failed.emit(str(exc))
