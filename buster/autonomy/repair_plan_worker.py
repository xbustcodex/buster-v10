from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from buster.autonomy.repair_planner import RepairPlanner


class RepairPlanWorker(QObject):
    """
    Background worker for generating a repair plan.

    Runs RepairPlanner.plan() inside a QThread so the UI
    remains responsive while the AI is planning.

    Signals
    -------
    finished(object)
        Emits a RepairPlan instance on success.

    failed(str)
        Emits an error message if planning fails.
    """

    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        planner: RepairPlanner,
        finding: dict[str, Any],
        review: dict[str, Any],
    ) -> None:
        super().__init__()

        self._planner = planner
        self._finding = dict(finding)
        self._review = dict(review)

    @Slot()
    def run(self) -> None:
        """
        Execute the repair planner.
        """

        try:
            result = self._planner.plan(
                self._finding,
                self._review,
            )

            self.finished.emit(result)

        except Exception as exc:
            self.failed.emit(str(exc))