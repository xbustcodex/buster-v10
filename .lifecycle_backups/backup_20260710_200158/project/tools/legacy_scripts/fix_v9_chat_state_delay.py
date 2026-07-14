from pathlib import Path

p = Path("buster/ui/v9/chat_view.py")
text = p.read_text(encoding="utf-8")

if "from PySide6.QtCore import QTimer" not in text:
    text = text.replace(
        "from PySide6.QtCore import Qt, QTime",
        "from PySide6.QtCore import Qt, QTime, QTimer",
    )

text = text.replace(
'''        self.add_card(reply, False)
        if self.on_state:
            self.on_state("idle")''',
'''        self.add_card(reply, False)
        if self.on_state:
            QTimer.singleShot(1200, lambda: self.on_state("idle"))'''
)

p.write_text(text, encoding="utf-8")
print("Added face state delay.")