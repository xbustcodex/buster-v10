from PySide6.QtCore import QObject, QTimer, Signal


class RuntimeMonitor(QObject):
    updated = Signal(dict)
    error = Signal(str)

    def __init__(self, runtime_core=None, interval_ms=1000, parent=None):
        super().__init__(parent)
        self.runtime_core = runtime_core

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(interval_ms)

    def refresh(self):
        if not self.runtime_core:
            self.error.emit("Runtime core not connected.")
            return

        try:
            payload = {
                "status": self.runtime_core.status(),
                "devtools": self.runtime_core.devtools.dashboard_payload(),
                "jobs": self.runtime_core.jobs.status(),
                "agents": self.runtime_core.agents.status(),
                "blackboard": self.runtime_core.blackboard.snapshot(),
                "agent_memory": self.runtime_core.agent_memory.status(),
                "events": self.runtime_core.events.recent(25),
            }
            self.updated.emit(payload)

        except Exception as e:
            self.error.emit(str(e))