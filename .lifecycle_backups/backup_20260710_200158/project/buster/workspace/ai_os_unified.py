from buster.ai_os import BusterAIOS


class UnifiedAIOSWorkspace:
    """Mission Control friendly wrapper for the v4 AI OS integration."""

    def __init__(self, root=None):
        self.aios = BusterAIOS(root=root)

    def submit_command(self, text: str):
        return self.aios.think(text)

    def get_status(self):
        return self.aios.status()
