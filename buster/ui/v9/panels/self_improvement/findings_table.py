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


class FindingsTable(QFrame):
    """
    Displays Self Improvement findings.

    Data source:
        SelfImprovementService.scan()

    Expected finding format:

        {
            "category": "tests",
            "title": "Repair failing tests",
            "description": "...",
            "severity": "high",
            "file": "buster/runtime/core.py",
            "line": 120,
            "confidence": 0.95,
        }

    Signals
    -------
    finding_selected(dict)
        Emitted when a row is selected.

    finding_activated(dict)
        Emitted when a row is double-clicked.
    """

    finding_selected = Signal(dict)
    finding_activated = Signal(dict)

    HEADERS = [
        "Severity",
        "Category",
        "Title",
        "File",
        "Confidence",
    ]

    SEVERITY = {
        "critical": {
            "label": "CRITICAL",
            "color": "#ef4444",
        },
        "high": {
            "label": "HIGH",
            "color": "#ef4444",
        },
        "medium": {
            "label": "MEDIUM",
            "color": "#f59e0b",
        },
        "low": {
            "label": "LOW",
            "color": "#eab308",
        },
        "info": {
            "label": "INFO",
            "color": "#38bdf8",
        },
    }

    def __init__(
        self,
        runtime_core=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.findings: list[dict[str, Any]] = []

        self.setObjectName(
            "SelfImprovementFindingsTable"
        )

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        layout.setSpacing(8)

        title = QLabel(
            "Findings",
            self,
        )
        title.setObjectName(
            "FindingsTableTitle"
        )

        self.summary_label = QLabel(
            "No findings",
            self,
        )
        self.summary_label.setObjectName(
            "FindingsTableSummary"
        )

        layout.addWidget(title)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(
            self,
        )

        self.table.setColumnCount(
            len(self.HEADERS)
        )

        self.table.setHorizontalHeaderLabels(
            self.HEADERS
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.table.setAlternatingRowColors(
            False
        )

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
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

        layout.addWidget(
            self.table
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementFindingsTable {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QLabel#FindingsTableTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#FindingsTableSummary {
                color: #94a3b8;
                font-size: 11px;
            }

            QTableWidget {
                background-color: #111827;
                color: #dbe3eb;
                border: 1px solid #293548;
                gridline-color: #202938;
                font-size: 11px;
            }

            QTableWidget::item {
                padding: 5px;
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
                font-size: 10px;
                font-weight: 700;
            }
            """
        )

    def set_findings(
        self,
        findings: Iterable[Any],
    ) -> None:
        """
        Replace all displayed findings.
        """
        self.findings = [
            self._normalise_finding(item)
            for item in findings
        ]

        self._render()

    def refresh(self) -> None:
        """
        Pull findings from the runtime service.
        """
        service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )

        scanner = getattr(
            service,
            "scan",
            None,
        )

        if not callable(scanner):
            return

        try:
            self.set_findings(
                scanner()
            )
        except Exception as exc:
            self.summary_label.setText(
                f"Scan error: {exc}"
            )

    def selected_finding(
        self,
    ) -> Optional[dict[str, Any]]:
        row = self.table.currentRow()

        if row < 0:
            return None

        if row >= len(self.findings):
            return None

        return self.findings[row]

    def clear(self) -> None:
        self.findings = []
        self.table.setRowCount(0)
        self.summary_label.setText(
            "No findings"
        )

    def _render(self) -> None:
        self.table.setRowCount(
            len(self.findings)
        )

        for row, finding in enumerate(
            self.findings
        ):
            severity = str(
                finding.get(
                    "severity",
                    "info",
                )
            ).lower()

            severity_data = self.SEVERITY.get(
                severity,
                self.SEVERITY["info"],
            )

            severity_item = QTableWidgetItem(
                severity_data["label"]
            )

            severity_item.setForeground(
                QBrush(
                    QColor(
                        severity_data["color"]
                    )
                )
            )

            self.table.setItem(
                row,
                0,
                severity_item,
            )

            self.table.setItem(
                row,
                1,
                self._item(
                    finding.get(
                        "category",
                        "",
                    )
                ),
            )

            self.table.setItem(
                row,
                2,
                self._item(
                    finding.get(
                        "title",
                        finding.get(
                            "description",
                            "",
                        ),
                    )
                ),
            )

            file_text = finding.get(
                "file",
                "",
            )

            line = finding.get(
                "line",
                0,
            )

            if line:
                file_text = (
                    f"{file_text}:{line}"
                )

            self.table.setItem(
                row,
                3,
                self._item(file_text),
            )

            confidence = finding.get(
                "confidence",
                0,
            )

            try:
                confidence_text = (
                    f"{float(confidence) * 100:.0f}%"
                )
            except Exception:
                confidence_text = str(
                    confidence
                )

            self.table.setItem(
                row,
                4,
                self._item(
                    confidence_text
                ),
            )

        self.summary_label.setText(
            f"{len(self.findings)} finding(s)"
        )

        self.table.resizeRowsToContents()

    def _selection_changed(self) -> None:
        finding = self.selected_finding()

        if finding:
            self.finding_selected.emit(
                finding
            )

    def _double_clicked(
        self,
        row: int,
        column: int,
    ) -> None:
        if row < 0:
            return

        if row >= len(self.findings):
            return

        self.finding_activated.emit(
            self.findings[row]
        )

    @staticmethod
    def _item(
        value: Any,
    ) -> QTableWidgetItem:
        return QTableWidgetItem(
            str(value or "")
        )

    @staticmethod
    def _normalise_finding(
        finding: Any,
    ) -> dict[str, Any]:
        if isinstance(
            finding,
            Mapping,
        ):
            return dict(finding)

        if hasattr(
            finding,
            "to_dict",
        ):
            try:
                return dict(
                    finding.to_dict()
                )
            except Exception:
                pass

        return {
            "title": str(finding),
            "description": str(finding),
            "severity": "info",
            "confidence": 0,
        }
