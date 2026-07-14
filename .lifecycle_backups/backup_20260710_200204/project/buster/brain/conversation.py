class ConversationManager:
    def __init__(self, max_items=20):
        self.max_items = max_items
        self.items = []

    def add_user(self, text):
        self.items.append(("user", text))
        self._trim()

    def add_assistant(self, text):
        self.items.append(("assistant", text))
        self._trim()

    def _trim(self):
        self.items = self.items[-self.max_items:]

    def summary(self):
        return "\n".join([f"{role}: {text}" for role, text in self.items[-8:]])
