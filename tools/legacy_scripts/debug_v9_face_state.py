from pathlib import Path

p = Path("buster/ui/v9/main_window.py")
text = p.read_text(encoding="utf-8")

text = text.replace(
'''    def set_face_state(self, state):
        self.current_face_state = state
        if self.face_window is not None:
            self.face_window.set_state(state)
''',
'''    def set_face_state(self, state):
        print("FACE STATE:", state)
        self.current_face_state = state
        if self.face_window is not None:
            self.face_window.set_state(state)
'''
)

p.write_text(text, encoding="utf-8")
print("Debug print added.")