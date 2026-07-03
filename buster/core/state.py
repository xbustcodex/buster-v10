class AppState:
    def __init__(self):
        self.mode = "standby"
        self.compact = False

    def set_mode(self, mode: str):
        self.mode = mode
