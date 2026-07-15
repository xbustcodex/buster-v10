from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
)


class RuntimeStatsBar(QFrame):
    """
    Displays live Runtime Timeline statistics.

    This widget is display-only.

    TimelinePanel owns the logic and periodically calls:

        update_stats({...})
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("RuntimeStatsBar")

        self.setStyleSheet("""
        QFrame#RuntimeStatsBar{
            background:#081321;
            border:1px solid #17385B;
            border-radius:10px;
        }

        QLabel{
            border:none;
            background:transparent;
        }

        QLabel.title{
            color:#86A6C8;
            font-size:11px;
            font-weight:600;
        }

        QLabel.value{
            color:white;
            font-size:18px;
            font-weight:700;
        }
        """)

        self._build()

    # ----------------------------------------------------

    def _build(self):

        layout = QGridLayout(self)

        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(4)

        self.events_value = self._cell(
            layout,
            0,
            "Events",
            "0",
        )

        self.visible_value = self._cell(
            layout,
            1,
            "Visible",
            "0",
        )

        self.filtered_value = self._cell(
            layout,
            2,
            "Filtered",
            "0",
        )

        self.rate_value = self._cell(
            layout,
            3,
            "Events/sec",
            "0",
        )

        self.subscribers_value = self._cell(
            layout,
            4,
            "Subscribers",
            "0",
        )

        self.dispatcher_value = self._cell(
            layout,
            5,
            "Dispatcher",
            "Healthy",
        )

        self.paused_value = self._cell(
            layout,
            6,
            "Paused",
            "No",
        )

    # ----------------------------------------------------

    def _cell(
        self,
        layout,
        column,
        title,
        value,
    ):

        title_label = QLabel(title)
        title_label.setProperty("class", "title")

        value_label = QLabel(value)
        value_label.setProperty("class", "value")
        value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(
            title_label,
            0,
            column,
        )

        layout.addWidget(
            value_label,
            1,
            column,
        )

        return value_label

    # ----------------------------------------------------

    def update_stats(self, stats: dict):

        self.events_value.setText(
            str(stats.get("events", 0))
        )

        self.visible_value.setText(
            str(stats.get("visible", 0))
        )

        self.filtered_value.setText(
            str(stats.get("filtered", 0))
        )

        self.rate_value.setText(
            str(stats.get("events_per_second", 0))
        )

        self.subscribers_value.setText(
            str(stats.get("subscribers", 0))
        )

        self.dispatcher_value.setText(
            str(stats.get("dispatcher", "Unknown"))
        )

        self.paused_value.setText(
            "Yes"
            if stats.get("paused", False)
            else "No"
        )

    # ----------------------------------------------------

    def reset(self):

        self.update_stats({
            "events": 0,
            "visible": 0,
            "filtered": 0,
            "events_per_second": 0,
            "subscribers": 0,
            "dispatcher": "Healthy",
            "paused": False,
        })