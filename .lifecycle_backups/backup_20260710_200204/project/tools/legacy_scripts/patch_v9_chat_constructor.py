from pathlib import Path

path = Path("buster/ui/v9/main_window.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
"        self.chat = ChatView(self.live, self.refresh_live)",
"        self.chat = ChatView(self.live, self.refresh_live, self.set_face_state)"
)

path.write_text(text, encoding="utf-8")
print("V9 chat now controls avatar state.")
