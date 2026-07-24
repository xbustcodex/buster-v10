from __future__ import annotations

import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QFrame,
    QGridLayout,
)


class RuntimeMetricCard(QFrame):
    def __init__(self, title: str, value: str = "0"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.title = QLabel(title)
        self.value = QLabel(value)

        self.title.setStyleSheet("font-size: 12px; color: #9aa4b2;")
        self.value.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))


class BusterLiveRuntimeUI(QWidget):
    def __init__(
        self,
        parent=None,
        live=None,
        runtime_core=None,
        **kwargs,
    ):
        super().__init__(parent)

        self.live = live
        self.runtime_core = runtime_core or getattr(live, "runtime_core", None)

        if self.runtime_core is None:
            raise RuntimeError(
                "BusterLiveRuntimeUI requires the application runtime_core."
            )

        self.core = self.runtime_core

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QHBoxLayout()

        title = QLabel("Buster Desktop AI OS v11 — Live Runtime Console")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        self.refresh_btn = QPushButton("Refresh")
        self.tick_btn = QPushButton("Tick")
        self.run_demo_btn = QPushButton("Run Demo Workflow")
        self.health_btn = QPushButton("Health Job")

        header.addWidget(title, 1)
        header.addWidget(self.refresh_btn)
        header.addWidget(self.tick_btn)
        header.addWidget(self.run_demo_btn)
        header.addWidget(self.health_btn)

        root.addLayout(header)

        cards = QGridLayout()

        self.runtime_card = RuntimeMetricCard("Runtime", "Running")
        self.services_card = RuntimeMetricCard("Services", "0")
        self.agents_card = RuntimeMetricCard("Agents", "0")
        self.jobs_card = RuntimeMetricCard("Jobs", "0")
        self.events_card = RuntimeMetricCard("Events", "0")
        self.plugins_card = RuntimeMetricCard("Plugins", "0")

        for index, card in enumerate([
            self.runtime_card,
            self.services_card,
            self.agents_card,
            self.jobs_card,
            self.events_card,
            self.plugins_card,
        ]):
            cards.addWidget(card, index // 3, index % 3)

        root.addLayout(cards)

        self.tabs = QTabWidget()

        self.overview_tab = QTextEdit()
        self.services_tab = QTextEdit()
        self.agents_tab = QTextEdit()
        self.jobs_tab = QTextEdit()
        self.events_tab = QTextEdit()
        self.blackboard_tab = QTextEdit()
        self.memory_tab = QTextEdit()
        self.plugins_tab = QTextEdit()
        self.workflow_tab = QTextEdit()

        for widget in [
            self.overview_tab,
            self.services_tab,
            self.agents_tab,
            self.jobs_tab,
            self.events_tab,
            self.blackboard_tab,
            self.memory_tab,
            self.plugins_tab,
            self.workflow_tab,
        ]:
            widget.setReadOnly(True)

        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.services_tab, "Services")
        self.tabs.addTab(self.agents_tab, "Agents")
        self.tabs.addTab(self.jobs_tab, "Jobs")
        self.tabs.addTab(self.events_tab, "Events")
        self.tabs.addTab(self.blackboard_tab, "Blackboard")
        self.tabs.addTab(self.memory_tab, "Agent Memory")
        self.tabs.addTab(self.plugins_tab, "Plugins")
        self.tabs.addTab(self.workflow_tab, "Workflow Graph")

        root.addWidget(self.tabs, 1)

        self.refresh_btn.clicked.connect(self.refresh)
        self.tick_btn.clicked.connect(self.tick)
        self.run_demo_btn.clicked.connect(self.run_demo_workflow)
        self.health_btn.clicked.connect(self.run_health_job)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2500)

        self.refresh()

    def pretty(self, data):
        return json.dumps(data, indent=4, default=str)

    def refresh(self):
        payload = self.core.devtools.dashboard_payload()
        status = self.core.status()

        runtime = payload["runtime"]
        jobs = payload["jobs"]
        plugins = payload["plugins"]

        self.runtime_card.set_value("Running" if status.get("started") else "Stopped")
        self.services_card.set_value(len(runtime.get("services", [])))
        self.agents_card.set_value(len(runtime.get("agents", [])))
        self.jobs_card.set_value(jobs.get("count", 0))
        self.events_card.set_value(runtime.get("event_count", 0))
        self.plugins_card.set_value(plugins.get("count", 0))

        self.overview_tab.setPlainText(self.pretty(runtime))
        self.services_tab.setPlainText(self.pretty(payload["services"]))
        self.agents_tab.setPlainText(self.pretty(payload["agents"]))
        self.jobs_tab.setPlainText(self.pretty(payload["jobs"]))
        self.events_tab.setPlainText(self.pretty(payload["events"]))
        self.blackboard_tab.setPlainText(self.pretty(self.core.blackboard.snapshot()))
        self.memory_tab.setPlainText(self.pretty(self.core.agent_memory.status()))
        self.plugins_tab.setPlainText(self.pretty(plugins))
        self.workflow_tab.setPlainText(self.pretty({
            "workflow_graph": payload["workflow_graph"],
            "event_graph": payload["event_graph"],
        }))

    def tick(self):
        self.core.tick([{
            "type": "ui",
            "summary": "Live Runtime Console tick requested",
        }])
        self.refresh()

    def run_demo_workflow(self):
        self.core.run("Review architecture quality and validate with tests")
        self.refresh()

    def run_health_job(self):
        job = self.core.create_job(
            "Live Runtime Health Check",
            "lifecycle.health",
            {"requested_by": "live_runtime_ui"},
        )
        self.core.run_job(job["job_id"])
        self.refresh()