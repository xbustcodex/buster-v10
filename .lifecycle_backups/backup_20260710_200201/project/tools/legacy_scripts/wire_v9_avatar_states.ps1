@'
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from buster.ui.v9.theme import STYLE
from buster.ui.v9.widgets.animated_avatar import AnimatedAvatar

class FaceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buster Face")
        self.resize(320, 340)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        self.avatar = AnimatedAvatar("idle")
        layout.addWidget(self.avatar)

    def set_state(self, state):
        self.avatar.set_state(state)
'@ | Set-Content "buster/ui/v9/face_window.py"

@'
from pathlib import Path

path = Path("buster/ui/v9/main_window.py")
text = path.read_text(encoding="utf-8")

if "def set_face_state" not in text:
    text = text.replace(
'''    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.show()
        self.face_window.raise_()
''',
'''    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.show()
        self.face_window.raise_()

    def set_face_state(self, state):
        if self.face_window is not None:
            self.face_window.set_state(state)
'''
    )

path.write_text(text, encoding="utf-8")
print("Main window face state bridge installed.")
'@ | Set-Content "patch_v9_main_face_state.py"

python patch_v9_main_face_state.py

@'
from pathlib import Path

path = Path("buster/ui/v9/chat_view.py")
text = path.read_text(encoding="utf-8")

# Let ChatView accept on_state callback
text = text.replace(
"    def __init__(self, live, on_message=None):\n        super().__init__()\n        self.live = live\n        self.on_message = on_message\n        self.build()",
"    def __init__(self, live, on_message=None, on_state=None):\n        super().__init__()\n        self.live = live\n        self.on_message = on_message\n        self.on_state = on_state\n        self.build()"
)

# Set thinking / idle around brain call
text = text.replace(
'''        try:
            reply = self.live.brain(text)
        except Exception as exc:
            reply = f"Command failed: {exc}"

        self.add_card(reply, False)''',
'''        try:
            if self.on_state:
                self.on_state("thinking")
            reply = self.live.brain(text)
            if self.on_state:
                self.on_state("speaking")
        except Exception as exc:
            reply = f"Command failed: {exc}"
            if self.on_state:
                self.on_state("error")

        self.add_card(reply, False)
        if self.on_state:
            self.on_state("idle")'''
)

path.write_text(text, encoding="utf-8")
print("ChatView avatar state hooks installed.")
'@ | Set-Content "patch_v9_chat_avatar_state.py"

python patch_v9_chat_avatar_state.py

@'
from pathlib import Path

path = Path("buster/ui/v9/main_window.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
"        self.chat = ChatView(self.live, self.refresh_live)",
"        self.chat = ChatView(self.live, self.refresh_live, self.set_face_state)"
)

path.write_text(text, encoding="utf-8")
print("V9 chat now controls avatar state.")
'@ | Set-Content "patch_v9_chat_constructor.py"

python patch_v9_chat_constructor.py

Write-Host "Animated avatar state wiring complete."