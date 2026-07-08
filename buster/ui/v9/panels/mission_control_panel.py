from __future__ import annotations

import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QFrame, QSplitter
)

from buster.runtime import create_runtime_core


class MissionControlV12(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.core = create_runtime_core(".")
        self.core.start()

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Buster Desktop AI OS — Mission Control 3.0")
        title.setStyleSheet("font-size:26px;font-weight:bold;")
        self.refresh_btn = QPushButton("Refresh")
        self.workflow_btn = QPushButton("Run Workflow")
        self.health_btn = QPushButton("Health")

        header.addWidget(title, 1)
        header.addWidget(self.refresh_btn)
        header.addWidget(self.workflow_btn)
        header.addWidget(self.health_btn)
        root.addLayout(header)

        split = QSplitter(Qt.Horizontal)

        self.nav = QListWidget()
        for name in ["Dashboard", "Runtime", "Services", "Agents", "Jobs", "Events", "Blackboard", "Memory", "Plugins", "Workflow"]:
            self.nav.addItem(QListWidgetItem(name))

        self.main = QTextEdit()
        self.main.setReadOnly(True)

        self.inspector = QTextEdit()
        self.inspector.setReadOnly(True)

        split.addWidget(self.nav)
        split.addWidget(self.main)
        split.addWidget(self.inspector)

        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 4)
        split.setStretchFactor(2, 2)

        root.addWidget(split, 1)

        self.nav.currentItemChanged.connect(self.refresh)
        self.refresh_btn.clicked.connect(self.refresh)
        self.workflow_btn.clicked.connect(self.run_workflow)
        self.health_btn.clicked.connect(self.run_health)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2500)

        self.nav.setCurrentRow(0)
        self.refresh()

    def pretty(self, data):
        return json.dumps(data, indent=4, default=str)

    def payload(self):
        return self.core.devtools.dashboard_payload()

    def refresh(self):
        item = self.nav.currentItem()
        section = item.text() if item else "Dashboard"
        payload = self.payload()

        views = {
            "Dashboard": {
                "summary": payload["runtime"],
                "jobs": payload["jobs"].get("counts", {}),
                "recent_events": payload["events"][-8:],
            },
            "Runtime": self.core.status(),
            "Services": payload["services"],
            "Agents": payload["agents"],
            "Jobs": payload["jobs"],
            "Events": payload["events"],
            "Blackboard": self.core.blackboard.snapshot(),
            "Memory": self.core.agent_memory.status(),
            "Plugins": payload["plugins"],
            "Workflow": {
                "workflow_graph": payload["workflow_graph"],
                "event_graph": payload["event_graph"],
            },
        }

        self.main.setPlainText(self.pretty(views.get(section, {})))

        self.inspector.setPlainText(self.pretty({
            "selected": section,
            "runtime_started": self.core.status().get("started"),
            "services": len(payload["runtime"].get("services", [])),
            "agents": len(payload["runtime"].get("agents", [])),
            "jobs": payload["jobs"].get("count", 0),
            "events": payload["runtime"].get("event_count", 0),
            "capabilities": len(self.core.registry.status().get("capabilities", {})),
        }))

    def run_workflow(self):
        self.core.run("Review architecture quality and validate with tests")
        self.refresh()

    def run_health(self):
        job = self.core.create_job("Mission Control Health", "lifecycle.health", {"requested_by": "mission_control_v12"})
        self.core.run_job(job["job_id"])
        self.refresh()
