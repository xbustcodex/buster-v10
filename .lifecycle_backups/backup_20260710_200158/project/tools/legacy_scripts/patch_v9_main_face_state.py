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
