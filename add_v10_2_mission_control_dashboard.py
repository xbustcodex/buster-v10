from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/ui/v10/__init__.py": "",

    "buster/ui/v10/runtime_dashboard.py": r'''from __future__ import annotations

import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QGridLayout,
)

from buster.runtime.sdk_bootstrap import build_sdk_runtime


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "0"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.value = QLabel(value)

        self.title.setStyleSheet("font-size: 12px; color: #9aa4b2;")
        self.value.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))


class MissionControlRuntimeDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.system = build_sdk_runtime(".")
        self.runtime = self.system["runtime"]
        self.sdk = self.system["sdk"]
        self.agents = self.system["agents"]
        self.registry = self.system["registry"]
        self.jobs = self.system["jobs"]

        self.runtime.start()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Buster Desktop AI OS v10.2 — Mission Control")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        root.addWidget(title)

        cards = QGridLayout()
        self.runtime_card = MetricCard("Runtime", "Running")
        self.services_card = MetricCard("Services", "0")
        self.agents_card = MetricCard("Agents", "0")
        self.jobs_card = MetricCard("Jobs", "0")
        self.events_card = MetricCard("Events", "0")
        self.health_card = MetricCard("Health", "Unknown")

        for i, card in enumerate([
            self.runtime_card,
            self.services_card,
            self.agents_card,
            self.jobs_card,
            self.events_card,
            self.health_card,
        ]):
            cards.addWidget(card, i // 3, i % 3)

        root.addLayout(cards)

        buttons = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.tick_btn = QPushButton("Tick Runtime")
        self.health_job_btn = QPushButton("Run Health Job")
        self.verify_job_btn = QPushButton("Run Verify Job")
        self.backup_btn = QPushButton("Lifecycle Backup")

        for btn in [
            self.refresh_btn,
            self.tick_btn,
            self.health_job_btn,
            self.verify_job_btn,
            self.backup_btn,
        ]:
            buttons.addWidget(btn)

        root.addLayout(buttons)

        body = QHBoxLayout()

        self.services_box = QTextEdit()
        self.services_box.setReadOnly(True)
        self.services_box.setPlaceholderText("Services and agents")

        self.jobs_box = QTextEdit()
        self.jobs_box.setReadOnly(True)
        self.jobs_box.setPlaceholderText("Jobs")

        self.events_box = QTextEdit()
        self.events_box.setReadOnly(True)
        self.events_box.setPlaceholderText("Recent events")

        body.addWidget(self.services_box, 1)
        body.addWidget(self.jobs_box, 1)
        body.addWidget(self.events_box, 1)

        root.addLayout(body, 1)

        self.refresh_btn.clicked.connect(self.refresh)
        self.tick_btn.clicked.connect(self.tick_runtime)
        self.health_job_btn.clicked.connect(self.run_health_job)
        self.verify_job_btn.clicked.connect(self.run_verify_job)
        self.backup_btn.clicked.connect(self.run_backup)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)

        self.refresh()

    def pretty(self, data):
        return json.dumps(data, indent=4, default=str)

    def refresh(self):
        registry_status = self.registry.status()
        summary = registry_status.get("summary", {})
        job_status = self.jobs.status()
        events = self.sdk.events.recent(30)

        self.runtime_card.set_value("Running")
        self.services_card.set_value(summary.get("services", 0))
        self.agents_card.set_value(summary.get("agents", 0))
        self.jobs_card.set_value(job_status.get("count", 0))
        self.events_card.set_value(len(self.sdk.events.history))

        health = "Unknown"
        for event in reversed(events):
            if event.get("type") == "lifecycle.health.updated":
                payload = event.get("payload", {})
                health = f"{payload.get('overall_score', 0)}%"
                break
        self.health_card.set_value(health)

        services_view = {
            "services": registry_status.get("services", {}),
            "agents": registry_status.get("agents", {}),
            "capabilities": registry_status.get("capabilities", {}),
        }

        self.services_box.setPlainText(self.pretty(services_view))
        self.jobs_box.setPlainText(self.pretty(job_status))
        self.events_box.setPlainText(self.pretty(events))

    def tick_runtime(self):
        self.runtime.tick_once([{
            "type": "workspace",
            "summary": "Mission Control runtime dashboard active",
        }])
        self.refresh()

    def run_health_job(self):
        job = self.agents.run("jobs", {
            "action": "create",
            "title": "Mission Control Health Check",
            "job_type": "lifecycle.health",
            "payload": {"requested_by": "mission_control"},
        })
        self.agents.run("jobs", {
            "action": "run",
            "job_id": job["job_id"],
        })
        self.refresh()

    def run_verify_job(self):
        job = self.agents.run("jobs", {
            "action": "create",
            "title": "Mission Control Verify Check",
            "job_type": "lifecycle.verify",
            "payload": {"requested_by": "mission_control"},
        })
        self.agents.run("jobs", {
            "action": "run",
            "job_id": job["job_id"],
        })
        self.refresh()

    def run_backup(self):
        self.agents.run("lifecycle", "backup")
        self.refresh()
''',

    "test_v10_2_mission_control_dashboard.py": r'''import sys
from PySide6.QtWidgets import QApplication

from buster.ui.v10.runtime_dashboard import MissionControlRuntimeDashboard


def main():
    app = QApplication(sys.argv)
    window = MissionControlRuntimeDashboard()
    window.resize(1400, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
''',

    "tests/test_v10_2_runtime_dashboard_import.py": r'''def test_v10_2_runtime_dashboard_imports():
    from buster.ui.v10.runtime_dashboard import MissionControlRuntimeDashboard
    assert MissionControlRuntimeDashboard is not None
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print()
print("Buster v10.2 Mission Control Runtime Dashboard added.")
print()
print("Run:")
print("  python test_v10_2_mission_control_dashboard.py")
print("  pytest")