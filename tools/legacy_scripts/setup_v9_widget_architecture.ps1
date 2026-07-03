New-Item -ItemType Directory -Force "buster/ui/v9/widgets" | Out-Null
New-Item -ItemType Directory -Force "buster/ui/v9/panels" | Out-Null
New-Item -ItemType Directory -Force "buster/ui/v9/assets/icons" | Out-Null
New-Item -ItemType Directory -Force "buster/ui/v9/assets/avatar" | Out-Null
New-Item -ItemType File -Force "buster/ui/v9/widgets/__init__.py" | Out-Null
New-Item -ItemType File -Force "buster/ui/v9/panels/__init__.py" | Out-Null

@'
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

class MessageCard(QFrame):
    def __init__(self, title, body, is_user=False):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        row = QHBoxLayout()
        name = QLabel(title)
        name.setStyleSheet("font-size:16px; font-weight:bold; color:#20a8ff;")
        row.addWidget(name)
        row.addStretch()
        layout.addLayout(row)

        text = QLabel(body)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.setStyleSheet("font-size:14px; color:#dcecff;")
        layout.addWidget(text)

        if not is_user:
            actions = QHBoxLayout()
            for label in ["Copy", "Save", "Open"]:
                actions.addWidget(QPushButton(label))
            actions.addStretch()
            layout.addLayout(actions)
'@ | Set-Content "buster/ui/v9/widgets/message_card.py"

@'
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class StatusCard(QFrame):
    def __init__(self, title, value="unknown"):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size:13px; color:#8ea6c8;")
        self.value = QLabel(value)
        self.value.setStyleSheet("font-size:18px; font-weight:bold; color:#35ff6b;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))
'@ | Set-Content "buster/ui/v9/widgets/status_card.py"

@'
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar

class MetricCard(QFrame):
    def __init__(self, title, value=0):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.label = QLabel(title)
        self.label.setStyleSheet("font-size:13px; color:#8ea6c8;")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.value = QLabel("0%")
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        layout.addWidget(self.value)
        self.set_value(value)

    def set_value(self, value):
        try:
            n = int(float(value))
        except Exception:
            n = 0
        self.bar.setValue(max(0, min(100, n)))
        self.value.setText(f"{n}%")
'@ | Set-Content "buster/ui/v9/widgets/metric_card.py"

@'
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class AnimatedAvatar(QFrame):
    STATES = {
        "idle": ["◕     ◕\n   ◡", "⌒     ⌒\n   ◡"],
        "listening": ["◉     ◉\n   ◡", "◕     ◕\n   ◡"],
        "thinking": ["◕     ◕\n   ▬", "⌒     ⌒\n   ▬"],
        "speaking": ["◕     ◕\n   ◠", "⌒     ⌒\n   ◠"],
        "coding": ["▣     ▣\n   ▬", "◕     ◕\n   ▬"],
        "success": ["⌒     ⌒\n   ◡", "◕     ◕\n   ◡"],
        "error": ["●     ●\n   ▬", "◕     ◕\n   ▬"],
    }

    def __init__(self, state="idle"):
        super().__init__()
        self.setObjectName("Card")
        self.state = state
        self.index = 0

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.face = QLabel()
        self.face.setAlignment(Qt.AlignCenter)
        self.face.setStyleSheet("font-size:64px; color:#20a8ff;")

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size:20px; font-weight:bold; color:#20a8ff;")

        layout.addWidget(self.face)
        layout.addWidget(self.label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(500)

        self.set_state(state)

    def set_state(self, state):
        self.state = state if state in self.STATES else "idle"
        self.index = 0
        self.label.setText(self.state.title())
        self.face.setText(self.STATES[self.state][0])

    def animate(self):
        frames = self.STATES.get(self.state, self.STATES["idle"])
        self.index = (self.index + 1) % len(frames)
        self.face.setText(frames[self.index])
'@ | Set-Content "buster/ui/v9/widgets/animated_avatar.py"

@'
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from buster.ui.v9.widgets.animated_avatar import AnimatedAvatar

class FacePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("Assistant")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.avatar = AnimatedAvatar("idle")
        layout.addWidget(self.avatar)

    def set_state(self, state):
        self.avatar.set_state(state)
'@ | Set-Content "buster/ui/v9/panels/face_panel.py"

@'
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
'@ | Set-Content "buster/ui/v9/panels/workspace_panel.py"

@'
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class ProjectPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Project Explorer")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Project tree coming next."))
'@ | Set-Content "buster/ui/v9/panels/project_panel.py"

Write-Host "v9 widget architecture installed."