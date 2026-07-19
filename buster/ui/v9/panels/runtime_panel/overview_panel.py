from __future__ import annotations

from PySide6.QtCore import Qt

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MetricCard(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "0",
        parent=None,
    ):
        super().__init__(parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(0)

        self.title = QLabel(title)
        self.value = QLabel(value)

        self.title.setStyleSheet(
            "font-size: 9px; color: #9aa4b2;"
        )

        self.value.setStyleSheet(
            """
            font-size: 14px;
            font-weight: 700;
            color: #ffffff;
            """
        )

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))


class HealthStatusRow(QWidget):
    STATUS_STYLES = {
        "healthy": {
            "icon": "✓",
            "icon_color": "#31D158",
            "background": "#0B3A1D",
            "border": "#146B31",
            "text": "#62F28A",
        },
        "warning": {
            "icon": "!",
            "icon_color": "#FFB020",
            "background": "#4A3505",
            "border": "#8A650D",
            "text": "#FFD04A",
        },
        "error": {
            "icon": "×",
            "icon_color": "#FF4D5A",
            "background": "#48151A",
            "border": "#8C2831",
            "text": "#FF7A84",
        },
        "critical": {
            "icon": "×",
            "icon_color": "#FF4D5A",
            "background": "#48151A",
            "border": "#8C2831",
            "text": "#FF7A84",
        },
        "unknown": {
            "icon": "?",
            "icon_color": "#8393A8",
            "background": "#172131",
            "border": "#33445A",
            "text": "#A9B8CA",
        },
    }

    def __init__(self, name: str, parent=None):
        super().__init__(parent)

        self.name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        self.icon = QLabel("?")
        self.icon.setFixedSize(20, 20)
        self.icon.setAlignment(Qt.AlignCenter)

        self.name_label = QLabel(name)
        self.name_label.setMinimumWidth(90)
        self.name_label.setStyleSheet(
            """
            color: #EAF2FF;
            font-size: 11px;
            font-weight: 700;
            """
        )


        self.badge = QLabel("Unknown")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setMinimumWidth(74)
        self.badge.setFixedHeight(22)

        self.score = QLabel("0%")
        self.score.setFixedWidth(38)
        self.score.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )
        self.score.setStyleSheet(
            """
            color: #DCE8F8;
            font-family: Consolas;
            font-size: 10px;
            font-weight: 700;
            """
        )

        layout.addWidget(self.icon)
        layout.addSpacing(8)
        layout.addWidget(self.name_label)

        layout.addStretch(1)

        layout.addWidget(self.badge)
        layout.addSpacing(8)
        layout.addWidget(self.score)

        self.set_status("unknown", 0)

    def set_status(
        self,
        status: str,
        score: int = 0,
    ):
        status = str(status or "unknown").lower()

        style = self.STATUS_STYLES.get(
            status,
            self.STATUS_STYLES["unknown"],
        )

        self.icon.setText(style["icon"])
        self.icon.setStyleSheet(
            f"""
            QLabel {{
                color: #071018;
                background: {style["icon_color"]};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 900;
            }}
            """
        )

        self.badge.setText(status.title())
        self.badge.setStyleSheet(
            f"""
            QLabel {{
                color: {style["text"]};
                background: {style["background"]};
                border: 1px solid {style["border"]};
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 800;
            }}
            """
        )

        self.score.setText(f"{int(score)}%")



class MissionControlRuntimeDashboard(QWidget):
    def __init__(
        self,
        runtime_core=None,
        parent=None,
    ):
        super().__init__(parent)

        self.runtime_core = runtime_core

        self.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Expanding,
        )

        self.build_ui()
        self.connect_signals()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)

        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        title = QLabel("Mission Control")
        title.setStyleSheet(
            """
            font-size: 14px;
            font-weight: 700;
            color: #23B8FF;
            """
        )

        root.addWidget(title)

        cards = QGridLayout()
        cards.setHorizontalSpacing(4)
        cards.setVerticalSpacing(4)

        self.runtime_card = MetricCard(
            "Runtime",
            "Unknown",
        )

        self.services_card = MetricCard(
            "Services",
            "0",
        )

        self.agents_card = MetricCard(
            "Agents",
            "0",
        )

        self.jobs_card = MetricCard(
            "Jobs",
            "0",
        )

        self.events_card = MetricCard(
            "Events",
            "0",
        )

        self.health_card = MetricCard(
            "Health",
            "Unknown",
        )

        metric_list = [
            self.runtime_card,
            self.services_card,
            self.agents_card,
            self.jobs_card,
            self.events_card,
            self.health_card,
        ]

        for index, card in enumerate(metric_list):
            row = index // 2
            column = index % 2
            cards.addWidget(card, row, column)

        root.addLayout(cards)

        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(4)

        row1 = QHBoxLayout()
        row2 = QHBoxLayout()

        row1.setSpacing(4)
        row2.setSpacing(4)

        self.refresh_btn = QPushButton("Refresh")
        self.tick_btn = QPushButton("Tick")
        self.health_job_btn = QPushButton("Health")
        self.verify_job_btn = QPushButton("Verify")
        self.backup_btn = QPushButton("Backup")

        button_style = (
            "font-size: 10px; padding: 3px 2px;"
        )

        for button in (
            self.refresh_btn,
            self.tick_btn,
            self.health_job_btn,
        ):
            button.setFixedHeight(22)
            button.setStyleSheet(button_style)
            row1.addWidget(button)

        for button in (
            self.verify_job_btn,
            self.backup_btn,
        ):
            button.setFixedHeight(22)
            button.setStyleSheet(button_style)
            row2.addWidget(button)

        buttons_layout.addLayout(row1)
        buttons_layout.addLayout(row2)

        root.addLayout(buttons_layout)

        from PySide6.QtCore import Qt

        self.health_panel = QFrame()
        self.health_panel.setObjectName("HealthPanel")

        self.health_panel.setStyleSheet(
            """
            QFrame#HealthPanel {
                background: #07111D;
                border: 1px solid #1675B8;
                border-radius: 7px;
             }
             """
        )

        health_layout = QHBoxLayout(
            self.health_panel
        )
        health_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )
        health_layout.setSpacing(14)

        # Left side: status rows
        status_container = QWidget()

        status_layout = QVBoxLayout(
            status_container
        )
        status_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        status_layout.setSpacing(3)

        self.health_rows = {}

        health_names = [
            "Runtime",
            "Dispatcher",
            "Agents",
            "Jobs",
            "Memory",
            "Services",
            "Registry",
            "Events",
        ]

        for name in health_names:
            row = HealthStatusRow(name)
            self.health_rows[
                name.lower()
            ] = row

            status_layout.addWidget(row)

        status_layout.addStretch(1)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet(
            "color: #24445F;"
        )

        # Right side: warnings and errors
        messages_container = QWidget()

        messages_layout = QVBoxLayout(
            messages_container
        )
        messages_layout.setContentsMargins(
            8,
            0,
            0,
            0,
        )
        messages_layout.setSpacing(5)

        warnings_title = QLabel(
            "Warnings"
        )
        warnings_title.setStyleSheet(
            """
            color: #FFB020;
            font-size: 12px;
            font-weight: 800;
            """
        )

        self.warnings_label = QLabel(
            "• None"
        )
        self.warnings_label.setWordWrap(True)
        self.warnings_label.setAlignment(
            Qt.AlignTop | Qt.AlignLeft
        )
        self.warnings_label.setStyleSheet(
            """
            color: #EAF2FF;
            font-size: 10px;
            padding-bottom: 8px;
            """
        )
        errors_title = QLabel(
            "Errors"
        )
        errors_title.setStyleSheet(
            """
            color: #FF4D5A;
            font-size: 12px;
            font-weight: 800;
            """
        )

        self.errors_label = QLabel(
            "• None"
        )
        self.errors_label.setWordWrap(True)
        self.errors_label.setAlignment(
            Qt.AlignTop | Qt.AlignLeft
        )
        self.errors_label.setStyleSheet(
            """
            color: #EAF2FF;
            font-size: 10px;
            """
        )

        messages_layout.addWidget(
            warnings_title
        )
        messages_layout.addWidget(
            self.warnings_label
        )
        messages_layout.addWidget(
            errors_title
        )
        messages_layout.addWidget(
            self.errors_label
        )
        messages_layout.addStretch(1)

        health_layout.addWidget(
            status_container,
            5,
        )
        health_layout.addWidget(divider)
        health_layout.addWidget(
            messages_container,
            4,
        )

        self.health_panel.setMinimumHeight(190)
        self.health_panel.setMaximumHeight(235)

        root.addWidget(
            self.health_panel
        )

        root.addStretch(1)

    def connect_signals(self):
        self.refresh_btn.clicked.connect(
            self.refresh
        )

        self.tick_btn.clicked.connect(
            self.tick_runtime
        )

        self.health_job_btn.clicked.connect(
            self.run_health_job
        )

        self.verify_job_btn.clicked.connect(
            self.run_verify_job
        )

        self.backup_btn.clicked.connect(
            self.run_backup
        )

    

    def refresh(self):
        if self.runtime_core is None:
            self.runtime_card.set_value("Unavailable")
            self.health_card.set_value("Unavailable")
            return

        try:
            snapshot = self.runtime_core.runtime_snapshot.capture(
                event_limit=30,
                activity_limit=30,
            )

            health = self.runtime_core.health_monitor.evaluate(
                snapshot
            )

        except Exception as exc:
            self.runtime_card.set_value("Error")
            self.health_card.set_value("Error")

            self.warnings_label.setText(
                "• Runtime health evaluation failed."
            )

            self.errors_label.setText(
                f"• {exc}"
            )


            return

        summary = snapshot.get(
            "summary",
            {},
        )

        runtime_status = snapshot.get(
            "runtime",
            {},
        )

        services_status = snapshot.get(
            "services",
            {},
        )

        jobs_status = snapshot.get(
            "jobs",
            {},
        )

        events_status = snapshot.get(
            "events",
            {},
        )

        events = events_status.get(
            "recent",
            [],
        )

        runtime_name = runtime_status.get(
            "status",
            "unknown",
        )

        self.runtime_card.set_value(
            str(runtime_name).title()
        )

        self.services_card.set_value(
            services_status.get(
                "count",
                0,
            )
        )

        self.agents_card.set_value(
            summary.get(
                "agents",
                0,
            )
        )

        self.jobs_card.set_value(
            summary.get(
                "jobs",
                0,
            )
        )

        self.events_card.set_value(
            summary.get(
                "events",
                0,
            )
        )

        health_name = health.get(
            "overall",
            "unknown",
        )

        health_score = health.get(
            "score",
            0,
        )

        self.health_card.set_value(
            f"{str(health_name).title()} ({health_score}%)"
        )

        checks = health.get(
            "checks",
            [],
        )

        for check in checks:
            name = str(
                check.get(
                    "name",
                    "",
                )
            ).lower()

            row = self.health_rows.get(
                name
            )

            if row is None:
                continue

            row.set_status(
                check.get(
                    "status",
                    "unknown",
                ),
                check.get(
                    "score",
                    0,
                ),
            )

        warnings = health.get(
            "warnings",
            [],
        )

        errors = health.get(
            "errors",
            [],
        )

        if warnings:
            warning_text = "\n".join(
                f"• {warning}"
                for warning in warnings
            )
        else:
            warning_text = "• None"

        if errors:
            error_text = "\n".join(
                f"• {error}"
                for error in errors
            )
        else:
            error_text = "• None"

        self.warnings_label.setText(
            warning_text
        )

        self.errors_label.setText(
            error_text
        )

    def tick_runtime(self):
        if self.runtime_core is None:
            return

        try:
            self.runtime_core.tick(
                [
                    {
                        "type": "workspace",
                        "summary": (
                            "Mission Control runtime "
                            "dashboard active"
                        ),
                    }
                ]
            )

        finally:
            self.refresh()

    def run_health_job(self):
        if self.runtime_core is None:
            return

        try:
            job = self.runtime_core.create_job(
                title="Mission Control Health Check",
                job_type="lifecycle.health",
                payload={
                    "requested_by": "mission_control",
                },
            )

            job_id = self.get_job_id(job)

            if job_id is not None:
                self.runtime_core.run_job(
                    job_id
                )

        finally:
            self.refresh()

    def run_verify_job(self):
        if self.runtime_core is None:
            return

        try:
            job = self.runtime_core.create_job(
                title="Mission Control Verify Check",
                job_type="lifecycle.verify",
                payload={
                    "requested_by": "mission_control",
                },
            )

            job_id = self.get_job_id(job)

            if job_id is not None:
                self.runtime_core.run_job(
                    job_id
                )

        finally:
            self.refresh()

    def run_backup(self):
        if self.runtime_core is None:
            return

        try:
            self.runtime_core.run_agent(
                "lifecycle",
                "backup",
            )

        finally:
            self.refresh()

    @staticmethod
    def get_job_id(job):
        if isinstance(job, dict):
            return (
                job.get("job_id")
                or job.get("id")
            )

        return (
            getattr(job, "job_id", None)
            or getattr(job, "id", None)
        )

    def shutdown(self):
        if self.timer.isActive():
            self.timer.stop()