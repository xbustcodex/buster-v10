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
