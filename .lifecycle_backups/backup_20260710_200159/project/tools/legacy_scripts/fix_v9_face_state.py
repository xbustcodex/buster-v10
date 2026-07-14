from pathlib import Path

p = Path("buster/ui/v9/main_window.py")
text = p.read_text(encoding="utf-8")

text = text.replace(
    "self.face_window = None\n        self.dashboard_window = None",
    "self.face_window = None\n        self.current_face_state = 'idle'\n        self.dashboard_window = None",
)

text = text.replace(
'''    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.show()
        self.face_window.raise_()

    def set_face_state(self, state):
        if self.face_window is not None:
            self.face_window.set_state(state)
''',
'''    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.set_state(self.current_face_state)
        self.face_window.show()
        self.face_window.raise_()

    def set_face_state(self, state):
        self.current_face_state = state
        if self.face_window is not None:
            self.face_window.set_state(state)
'''
)

p.write_text(text, encoding="utf-8")
print("Fixed persistent face state.")