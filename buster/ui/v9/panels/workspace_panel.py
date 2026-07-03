from PySide6.QtWidgets import QWidget, QGridLayout
from buster.ui.v9.widgets.status_card import StatusCard
from buster.ui.v9.widgets.metric_card import MetricCard

class WorkspacePanel(QWidget):
    def __init__(self, live):
        super().__init__()
        self.live = live
        layout = QGridLayout(self)

        self.project = StatusCard("Project")
        self.git = StatusCard("Git Branch")
        self.ai = StatusCard("AI Provider")
        self.python = StatusCard("Python")
        self.cpu = MetricCard("CPU")
        self.ram = MetricCard("RAM")

        layout.addWidget(self.project, 0, 0)
        layout.addWidget(self.git, 0, 1)
        layout.addWidget(self.ai, 1, 0)
        layout.addWidget(self.python, 1, 1)
        layout.addWidget(self.cpu, 2, 0)
        layout.addWidget(self.ram, 2, 1)

        self.refresh()

    def refresh(self):
        import psutil
        from pathlib import Path
        self.project.set_value(Path.cwd().name)
        self.git.set_value(self.live.git_branch())
        self.ai.set_value(self.live.safe(lambda: self.live.services.get("ai").quick_status(), "unknown"))
        self.python.set_value(self.live.python_version())
        self.cpu.set_value(psutil.cpu_percent())
        self.ram.set_value(psutil.virtual_memory().percent)
