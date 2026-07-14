from .context import AIOSContext
from .orchestrator import AIOSOrchestrator


class BusterAIOS:
    """Single public entry point for the integrated AI OS layer."""

    def __init__(self, root=None):
        context = AIOSContext(root=root) if root else AIOSContext()
        self.orchestrator = AIOSOrchestrator(context)

    def think(self, request: str):
        return self.orchestrator.plan(request)

    def status(self):
        return self.orchestrator.status().as_dict()
