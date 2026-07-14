from pathlib import Path

p = Path("buster/ui/v9/main_window.py")
text = p.read_text(encoding="utf-8")

text = text.replace(
    "from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel",
    "from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication",
)

text = text.replace(
'''    def set_face_state(self, state):
        print("FACE STATE:", state)
        self.current_face_state = state
        if self.face_window is not None:
            self.face_window.set_state(state)
''',
'''    def set_face_state(self, state):
        print("FACE STATE:", state)
        self.current_face_state = state

        if self.face_window is None:
            self.face_window = FaceWindow()
            self.face_window.show()

        self.face_window.set_state(state)
        self.face_window.raise_()
        QApplication.processEvents()
'''
)

p.write_text(text, encoding="utf-8")
print("Face repaint fix applied.")