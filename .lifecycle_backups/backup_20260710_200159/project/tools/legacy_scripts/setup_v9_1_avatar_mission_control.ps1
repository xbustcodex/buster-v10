@'
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget

class AvatarCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.pulse = 0
        self.setMinimumSize(220, 220)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(80)

    def set_state(self, state):
        self.state = state
        self.update()

    def tick(self):
        self.pulse = (self.pulse + 1) % 100
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2

        glow = 40 + (self.pulse % 40)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(32, 168, 255, 35))
        p.drawEllipse(cx - glow, cy - glow, glow * 2, glow * 2)

        p.setBrush(QColor(8, 20, 38))
        p.setPen(QPen(QColor(32, 168, 255), 4))
        p.drawEllipse(cx - 70, cy - 70, 140, 140)

        eye_y = cy - 20
        mouth_y = cy + 32

        if self.state == "thinking":
            eye_color = QColor(255, 210, 80)
            mouth = "flat"
        elif self.state == "speaking":
            eye_color = QColor(80, 255, 180)
            mouth = "open"
        elif self.state == "error":
            eye_color = QColor(255, 80, 80)
            mouth = "flat"
        elif self.state == "success":
            eye_color = QColor(80, 255, 120)
            mouth = "smile"
        else:
            eye_color = QColor(32, 168, 255)
            mouth = "smile"

        p.setBrush(eye_color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - 38, eye_y, 18, 18)
        p.drawEllipse(cx + 20, eye_y, 18, 18)

        p.setPen(QPen(eye_color, 5))

        if mouth == "open":
            p.drawEllipse(cx - 16, mouth_y - 8, 32, 22)
        elif mouth == "flat":
            p.drawLine(cx - 24, mouth_y, cx + 24, mouth_y)
        else:
            p.drawArc(cx - 30, mouth_y - 18, 60, 35, 200 * 16, 140 * 16)

        p.end()
'@ | Set-Content "buster/ui/v9/widgets/avatar_canvas.py"

@'
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from buster.ui.v9.widgets.avatar_canvas import AvatarCanvas

class AnimatedAvatar(QFrame):
    def __init__(self, state="idle"):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)

        self.canvas = AvatarCanvas()
        self.label = QLabel(state.title())
        self.label.setStyleSheet("font-size:20px; font-weight:bold; color:#20a8ff;")
        self.label.setAlignment(Qt.AlignCenter) if False else None

        layout.addWidget(self.canvas)
        layout.addWidget(self.label)

        self.set_state(state)

    def set_state(self, state):
        self.canvas.set_state(state)
        self.label.setText(state.title())
'@ | Set-Content "buster/ui/v9/widgets/animated_avatar.py"

@'
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
import psutil
from pathlib import Path

class MissionControl(QFrame):
    def __init__(self, live):
        super().__init__()
        self.live = live
        self.setObjectName("Card")
        self.rows = {}
        self.build()

    def build(self):
        layout = QVBoxLayout(self)

        title = QLabel("MISSION CONTROL")
        title.setStyleSheet("font-size:14px; font-weight:bold; color:#20a8ff;")
        layout.addWidget(title)

        for key in ["AI", "Project", "Git", "Voice", "Vision", "CPU", "RAM"]:
            label = QLabel()
            label.setStyleSheet("font-size:13px; color:#b7c9e8;")
            layout.addWidget(label)
            self.rows[key] = label

        self.refresh()

    def refresh(self):
        self.rows["AI"].setText("AI: " + self.live.safe(lambda: self.live.services.get("ai").quick_status(), "unknown"))
        self.rows["Project"].setText("Project: " + Path.cwd().name)
        self.rows["Git"].setText("Git: " + self.live.git_branch())
        self.rows["Voice"].setText("Voice: " + self.live.safe(lambda: self.live.services.get("voice").status(), "unknown"))
        self.rows["Vision"].setText("Vision: " + self.live.safe(lambda: self.live.services.get("vision").status(), "unknown"))
        self.rows["CPU"].setText(f"CPU: {psutil.cpu_percent()}%")
        self.rows["RAM"].setText(f"RAM: {psutil.virtual_memory().percent}%")
'@ | Set-Content "buster/ui/v9/widgets/mission_control.py"

@'
from pathlib import Path

p = Path("buster/ui/v9/sidebar.py")
text = p.read_text(encoding="utf-8")

if "MissionControl" not in text:
    text = text.replace(
        "from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton\n",
        "from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton\nfrom buster.ui.v9.widgets.mission_control import MissionControl\n",
    )

text = text.replace(
'''        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setStyleSheet("color:#b7c9e8; font-size:13px;")
        layout.addWidget(self.quick)''',
'''        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setStyleSheet("color:#b7c9e8; font-size:13px;")
        layout.addWidget(self.quick)

        self.mission = MissionControl(self.live)
        layout.addWidget(self.mission)'''
)

text = text.replace(
'''    def refresh(self):
        self.quick.setText(self.live.quick_info())''',
'''    def refresh(self):
        self.quick.setText(self.live.quick_info())
        if hasattr(self, "mission"):
            self.mission.refresh()'''
)

p.write_text(text, encoding="utf-8")
print("Mission Control wired into sidebar.")
'@ | Set-Content "patch_v9_1_sidebar.py"

python patch_v9_1_sidebar.py

Write-Host "Buster v9.1 Avatar Engine + Mission Control installed."