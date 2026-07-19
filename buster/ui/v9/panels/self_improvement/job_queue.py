from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class JobQueue(QFrame):
    """
    Displays Buster autonomy jobs.

    Data source:
        runtime_core.autonomy_engine

    Supports:
        - waiting jobs
        - running jobs
        - completed jobs
        - failed jobs

    Signals:
        job_selected(dict)
        job_activated(dict)
    """

    job_selected = Signal(dict)
    job_activated = Signal(dict)

    HEADERS = [
        "Status",
        "Title",
        "Agent",
        "Project",
        "Created",
    ]

    STATUS = {
        "pending": {
            "label": "WAITING",
            "color": "#f59e0b",
        },
        "queued": {
            "label": "QUEUED",
            "color": "#f59e0b",
        },
        "running": {
            "label": "RUNNING",
            "color": "#38bdf8",
        },
        "completed": {
            "label": "DONE",
            "color": "#22c55e",
        },
        "failed": {
            "label": "FAILED",
            "color": "#ef4444",
        },
    }

    def __init__(
        self,
        runtime_core=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.jobs: list[dict[str, Any]] = []

        self.setObjectName("SelfImprovementJobQueue")

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Job Queue", self)
        title.setObjectName("JobQueueTitle")

        self.summary = QLabel(
            "No jobs",
            self,
        )
        self.summary.setObjectName("JobQueueSummary")

        layout.addWidget(title)
        layout.addWidget(self.summary)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)

        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.table.itemSelectionChanged.connect(
            self._selection_changed
        )

        self.table.cellDoubleClicked.connect(
            self._double_clicked
        )

        layout.addWidget(self.table)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementJobQueue {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QLabel#JobQueueTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#JobQueueSummary {
                color: #94a3b8;
                font-size: 11px;
            }

            QTableWidget {
                background-color: #111827;
                color: #dbe3eb;
                border: 1px solid #293548;
                font-size: 11px;
            }

            QTableWidget::item:selected {
                background-color: #1d4ed8;
                color: white;
            }

            QHeaderView::section {
                background-color: #1f2937;
                color: #cbd5e1;
                padding: 6px;
                border: none;
                font-weight: 700;
            }
            """
        )

    def refresh(self) -> None:
        """
        Refresh jobs from the runtime autonomy engine.
        """
        engine = getattr(
            self.runtime_core,
            "autonomy_engine",
            None,
        )

        status = getattr(
            engine,
            "status",
            None,
        )

        if not callable(status):
            return

        try:
            data = status()

            jobs = (
                data.get("jobs")
                or data.get("recent_jobs")
                or []
            )

            self.set_jobs(jobs)

        except Exception as exc:
            self.summary.setText(
                f"Error: {exc}"
            )

    def set_jobs(
        self,
        jobs: Iterable[Any],
    ) -> None:
        self.jobs = [
            self._normalise_job(job)
            for job in jobs
        ]

        self._render()

    def selected_job(
        self,
    ) -> Optional[dict[str, Any]]:
        row = self.table.currentRow()

        if row < 0 or row >= len(self.jobs):
            return None

        return self.jobs[row]

    def _render(self) -> None:
        self.table.setRowCount(
            len(self.jobs)
        )

        for row, job in enumerate(self.jobs):

            status = str(
                job.get(
                    "status",
                    "pending",
                )
            ).lower()

            status_info = self.STATUS.get(
                status,
                self.STATUS["pending"],
            )

            item = QTableWidgetItem(
                status_info["label"]
            )

            item.setForeground(
                QBrush(
                    QColor(
                        status_info["color"]
                    )
                )
            )

            self.table.setItem(
                row,
                0,
                item,
            )

            self.table.setItem(
                row,
                1,
                self._item(
                    job.get(
                        "title",
                        job.get(
                            "request",
                            "",
                        ),
                    )
                ),
            )

            self.table.setItem(
                row,
                2,
                self._item(
                    job.get(
                        "agent",
                        "—",
                    )
                ),
            )

            self.table.setItem(
                row,
                3,
                self._item(
                    job.get(
                        "project",
                        "default",
                    )
                ),
            )

            self.table.setItem(
                row,
                4,
                self._item(
                    job.get(
                        "created_at",
                        "",
                    )
                ),
            )

        self.summary.setText(
            f"{len(self.jobs)} job(s)"
        )

    def _selection_changed(self) -> None:
        job = self.selected_job()

        if job:
            self.job_selected.emit(job)

    def _double_clicked(
        self,
        row: int,
        column: int,
    ) -> None:
        if 0 <= row < len(self.jobs):
            self.job_activated.emit(
                self.jobs[row]
            )

    @staticmethod
    def _item(value: Any) -> QTableWidgetItem:
        return QTableWidgetItem(
            str(value or "")
        )

    @staticmethod
    def _normalise_job(
        job: Any,
    ) -> dict[str, Any]:
        if isinstance(job, Mapping):
            return dict(job)

        if hasattr(job, "to_dict"):
            try:
                return dict(
                    job.to_dict()
                )
            except Exception:
                pass

        return {
            "title": str(job),
            "status": "pending",
        }
