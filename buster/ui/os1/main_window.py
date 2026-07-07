from __future__ import annotations

import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QSplitter, QFrame, QGridLayout
)

from buster.runtime import create_runtime_core


class OSMetric(QFrame):
    def __init__(self, title: str, value: str = "0"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.value = QLabel(value)
        self.title.setStyleSheet("color:#9aa4b2;font-size:12px;")
        self.value.setStyleSheet("font-size:24px;font-weight:bold;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))


class BusterAIOSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Buster Desktop AI OS 1.0")
        self.resize(1700, 980)

        self.core = create_runtime_core(".")
        self.core.start()

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Buster Desktop AI OS")
        title.setStyleSheet("font-size:28px;font-weight:bold;")
        self.status_label = QLabel("Runtime: Connected")
        self.status_label.setStyleSheet("color:#9aa4b2;")

        self.refresh_btn = QPushButton("Refresh")
        self.workflow_btn = QPushButton("Run Workflow")
        self.health_btn = QPushButton("Health")
        self.tick_btn = QPushButton("Tick")

        header.addWidget(title, 1)
        header.addWidget(self.status_label)
        header.addWidget(self.refresh_btn)
        header.addWidget(self.workflow_btn)
        header.addWidget(self.health_btn)
        header.addWidget(self.tick_btn)
        root.addLayout(header)

        self.metrics = QGridLayout()
        self.card_runtime = OSMetric("Runtime", "Running")
        self.card_services = OSMetric("Services", "0")
        self.card_agents = OSMetric("Agents", "0")
        self.card_jobs = OSMetric("Jobs", "0")
        self.card_events = OSMetric("Events", "0")
        self.card_plugins = OSMetric("Plugins", "0")

        for i, card in enumerate([
            self.card_runtime,
            self.card_services,
            self.card_agents,
            self.card_jobs,
            self.card_events,
            self.card_plugins,
        ]):
            self.metrics.addWidget(card, i // 3, i % 3)

        root.addLayout(self.metrics)

        splitter = QSplitter(Qt.Horizontal)

        self.nav = QListWidget()
        for name in [
            "Dashboard",
            "Mission Control",
            "Runtime",
            "Services",
            "Agents",
            "Jobs",
            "Workflow",
            "Events",
            "Plugins",
            "Projects",
            "Memory",
            "Voice",
            "Vision",
            "Terminal",
            "Settings",
        ]:
            self.nav.addItem(QListWidgetItem(name))

        self.workspace = QTextEdit()
        self.workspace.setReadOnly(True)

        self.inspector = QTextEdit()
        self.inspector.setReadOnly(True)

        splitter.addWidget(self.nav)
        splitter.addWidget(self.workspace)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 2)

        root.addWidget(splitter, 1)

        self.nav.currentItemChanged.connect(self.refresh)
        self.refresh_btn.clicked.connect(self.refresh)
        self.workflow_btn.clicked.connect(self.run_workflow)
        self.health_btn.clicked.connect(self.run_health)
        self.tick_btn.clicked.connect(self.tick)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2500)

        self.nav.setCurrentRow(0)
        self.refresh()

    def pretty(self, data):
        return json.dumps(data, indent=4, default=str)

    def dashboard_payload(self):
        return self.core.devtools.dashboard_payload()

    def refresh(self):
        payload = self.dashboard_payload()
        status = self.core.status()
        runtime = payload["runtime"]
        jobs = payload["jobs"]
        plugins = payload["plugins"]

        self.card_runtime.set_value("Running" if status.get("started") else "Stopped")
        self.card_services.set_value(len(runtime.get("services", [])))
        self.card_agents.set_value(len(runtime.get("agents", [])))
        self.card_jobs.set_value(jobs.get("count", 0))
        self.card_events.set_value(runtime.get("event_count", 0))
        self.card_plugins.set_value(plugins.get("count", 0))

        section = self.nav.currentItem().text() if self.nav.currentItem() else "Dashboard"

        views = {
            "Dashboard": {
                "runtime": runtime,
                "current_goal": self.core.blackboard.read("goal"),
                "jobs": jobs.get("counts", {}),
                "recent_events": payload["events"][-10:],
            },
            "Mission Control": {
                "summary": runtime,
                "workflow_graph": payload["workflow_graph"],
                "blackboard": self.core.blackboard.snapshot(),
            },
            "Runtime": status,
            "Services": payload["services"],
            "Agents": payload["agents"],
            "Jobs": jobs,
            "Workflow": {
                "workflow_graph": payload["workflow_graph"],
                "event_graph": payload["event_graph"],
            },
            "Events": payload["events"],
            "Plugins": payload["plugins"],
            "Projects": {
                "status": "placeholder",
                "message": "Project Intelligence will plug into Runtime Core here.",
            },
            "Memory": self.core.agent_memory.status(),
            "Voice": {
                "status": "not_connected",
                "message": "Voice Runtime will register here as a service.",
            },
            "Vision": {
                "status": "not_connected",
                "message": "Vision Runtime will register here as a service.",
            },
            "Terminal": {
                "status": "placeholder",
                "message": "Runtime terminal/command console will attach here.",
            },
            "Settings": {
                "runtime_root": status.get("root"),
                "started": status.get("started"),
            },
        }

        self.workspace.setPlainText(self.pretty(views.get(section, {})))

        self.inspector.setPlainText(self.pretty({
            "selected": section,
            "runtime_started": status.get("started"),
            "services": len(runtime.get("services", [])),
            "agents": len(runtime.get("agents", [])),
            "jobs": jobs.get("count", 0),
            "events": runtime.get("event_count", 0),
            "capabilities": len(self.core.registry.status().get("capabilities", {})),
        }))

    def run_workflow(self):
        self.core.run("Review architecture quality and validate with tests")
        self.refresh()

    def run_health(self):
        job = self.core.create_job("AI OS Health Check", "lifecycle.health", {"requested_by": "ai_os_shell"})
        self.core.run_job(job["job_id"])
        self.refresh()

    def tick(self):
        self.core.tick([{"type": "ui", "summary": "AI OS shell tick"}])
        self.refresh()
