from __future__ import annotations

import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QFrame, QGridLayout, QListWidget,
    QListWidgetItem, QSplitter
)


class Card(QFrame):
    def __init__(self, title: str, value: str = "0"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.value = QLabel(value)
        self.title.setStyleSheet("color:#9aa4b2;font-size:12px;")
        self.value.setStyleSheet("font-size:26px;font-weight:bold;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))


class RuntimeConsole(QWidget):
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
            raise RuntimeError("RuntimeConsole requires the application runtime_core.")

        self.core = self.runtime_core

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Buster Runtime Console")
        title.setStyleSheet("font-size:26px;font-weight:bold;")
        subtitle = QLabel("Live AI OS operations dashboard")
        subtitle.setStyleSheet("color:#9aa4b2;")

        title_col = QVBoxLayout()
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        self.refresh_btn = QPushButton("Refresh")
        self.tick_btn = QPushButton("Tick")
        self.workflow_btn = QPushButton("Run Workflow")
        self.health_btn = QPushButton("Health Job")
        self.verify_btn = QPushButton("Verify Job")

        header.addLayout(title_col, 1)
        for btn in [self.refresh_btn, self.tick_btn, self.workflow_btn, self.health_btn, self.verify_btn]:
            header.addWidget(btn)
        root.addLayout(header)

        cards = QGridLayout()
        self.card_runtime = Card("Runtime", "Running")
        self.card_services = Card("Services", "0")
        self.card_agents = Card("Agents", "0")
        self.card_jobs = Card("Jobs", "0")
        self.card_events = Card("Events", "0")
        self.card_health = Card("Health", "Unknown")
        self.card_plugins = Card("Plugins", "0")
        self.card_capabilities = Card("Capabilities", "0")

        for i, card in enumerate([
            self.card_runtime, self.card_services, self.card_agents, self.card_jobs,
            self.card_events, self.card_health, self.card_plugins, self.card_capabilities
        ]):
            cards.addWidget(card, i // 4, i % 4)

        root.addLayout(cards)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.overview = QTextEdit(); self.overview.setReadOnly(True)
        self.events = QTextEdit(); self.events.setReadOnly(True)
        self.jobs = QTextEdit(); self.jobs.setReadOnly(True)
        self.workflow = QTextEdit(); self.workflow.setReadOnly(True)
        self.blackboard = QTextEdit(); self.blackboard.setReadOnly(True)
        self.memory = QTextEdit(); self.memory.setReadOnly(True)
        self.plugins = QTextEdit(); self.plugins.setReadOnly(True)
        self.performance = QTextEdit(); self.performance.setReadOnly(True)
        self.inspector = QTextEdit(); self.inspector.setReadOnly(True)

        self.services_list = QListWidget()
        self.services_detail = QTextEdit(); self.services_detail.setReadOnly(True)
        service_split = QSplitter(Qt.Horizontal)
        service_split.addWidget(self.services_list)
        service_split.addWidget(self.services_detail)

        self.agents_list = QListWidget()
        self.agents_detail = QTextEdit(); self.agents_detail.setReadOnly(True)
        agent_split = QSplitter(Qt.Horizontal)
        agent_split.addWidget(self.agents_list)
        agent_split.addWidget(self.agents_detail)

        self.tabs.addTab(self.overview, "Overview")
        self.tabs.addTab(service_split, "Services")
        self.tabs.addTab(agent_split, "Agents")
        self.tabs.addTab(self.jobs, "Jobs")
        self.tabs.addTab(self.workflow, "Workflow")
        self.tabs.addTab(self.events, "Events")
        self.tabs.addTab(self.blackboard, "Blackboard")
        self.tabs.addTab(self.memory, "Agent Memory")
        self.tabs.addTab(self.plugins, "Plugins")
        self.tabs.addTab(self.performance, "Performance")
        self.tabs.addTab(self.inspector, "Inspector")

        self.refresh_btn.clicked.connect(self.refresh)
        self.tick_btn.clicked.connect(self.tick)
        self.workflow_btn.clicked.connect(self.run_workflow)
        self.health_btn.clicked.connect(self.run_health_job)
        self.verify_btn.clicked.connect(self.run_verify_job)
        self.services_list.itemClicked.connect(self.show_service)
        self.agents_list.itemClicked.connect(self.show_agent)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self._last_payload = {}
        self.refresh()

    def pretty(self, data):
        return json.dumps(data, indent=4, default=str)

    def refresh(self):
        payload = self.core.devtools.dashboard_payload()
        self._last_payload = payload

        runtime = payload["runtime"]
        registry = self.core.registry.status()
        jobs = payload["jobs"]
        plugins = payload["plugins"]
        events = payload["events"]

        self.card_runtime.set_value("Running" if self.core.status().get("started") else "Stopped")
        self.card_services.set_value(len(runtime.get("services", [])))
        self.card_agents.set_value(len(runtime.get("agents", [])))
        self.card_jobs.set_value(jobs.get("count", 0))
        self.card_events.set_value(runtime.get("event_count", 0))
        self.card_plugins.set_value(plugins.get("count", 0))
        self.card_capabilities.set_value(len(registry.get("capabilities", {})))

        health = "Unknown"
        for event in reversed(events):
            if event.get("type") == "lifecycle.health.updated":
                health = str(event.get("payload", {}).get("overall_score", "Unknown")) + "%"
                break
        self.card_health.set_value(health)

        self.overview.setPlainText(self.pretty(runtime))
        self.jobs.setPlainText(self.pretty(jobs))
        self.workflow.setPlainText(self.pretty({
            "workflow_graph": payload["workflow_graph"],
            "event_graph": payload["event_graph"],
        }))
        self.events.setPlainText(self.pretty(events))
        self.blackboard.setPlainText(self.pretty(self.core.blackboard.snapshot()))
        self.memory.setPlainText(self.pretty(self.core.agent_memory.status()))
        self.plugins.setPlainText(self.pretty(plugins))
        self.performance.setPlainText(self.pretty(self.performance_snapshot()))
        self.inspector.setPlainText(self.pretty(self.core.devtools.inspector.full_report()))

        self.populate_lists()

    def populate_lists(self):
        services = self._last_payload.get("services", {})
        agents = self._last_payload.get("agents", {})

        selected_service = self.services_list.currentItem().text() if self.services_list.currentItem() else None
        selected_agent = self.agents_list.currentItem().text() if self.agents_list.currentItem() else None

        self.services_list.clear()
        for name in sorted(services.keys()):
            item = QListWidgetItem(name)
            self.services_list.addItem(item)

        self.agents_list.clear()
        for name in sorted(agents.keys()):
            item = QListWidgetItem(name)
            self.agents_list.addItem(item)

        if selected_service and selected_service in services:
            self.services_detail.setPlainText(self.pretty(services[selected_service]))

        if selected_agent and selected_agent in agents:
            self.agents_detail.setPlainText(self.pretty(agents[selected_agent]))

    def show_service(self, item):
        services = self._last_payload.get("services", {})
        self.services_detail.setPlainText(self.pretty(services.get(item.text(), {})))

    def show_agent(self, item):
        agents = self._last_payload.get("agents", {})
        self.agents_detail.setPlainText(self.pretty(agents.get(item.text(), {})))

    def performance_snapshot(self):
        return {
            "event_count": len(self.core.events.history),
            "job_count": self.core.jobs.status().get("count", 0),
            "agent_count": len(self.core.agents.names()),
            "service_count": len(self.core.sdk.registry.names()),
            "blackboard_items": len(self.core.blackboard.snapshot()),
            "memory_agents": len(self.core.agent_memory.status().get("agents", {})),
            "note": "CPU/memory/thread metrics can be added later with psutil.",
        }

    def tick(self):
        self.core.tick([{"type": "ui", "summary": "Runtime console tick"}])
        self.refresh()

    def run_workflow(self):
        self.core.run("Review architecture quality and validate with tests")
        self.refresh()

    def run_health_job(self):
        job = self.core.create_job("Runtime Console Health Check", "lifecycle.health", {"requested_by": "runtime_console"})
        self.core.run_job(job["job_id"])
        self.refresh()

    def run_verify_job(self):
        job = self.core.create_job("Runtime Console Verify Check", "lifecycle.verify", {"requested_by": "runtime_console"})
        self.core.run_job(job["job_id"])
        self.refresh()