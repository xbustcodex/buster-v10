import sys
from PySide6.QtWidgets import QApplication
from buster.config.settings import Settings
from buster.core.events import EventBus
from buster.core.state import AppState
from buster.core.logger import Logger
from buster.core.container import ServiceContainer
from buster.services.thread_pool import ThreadPool
from buster.services.service_manager import ServiceManager
from buster.services.performance_monitor import PerformanceMonitor
from buster.services.task_scheduler import TaskScheduler
from buster.system.monitor import SystemMonitor
from buster.memory.engine import MemoryEngine
from buster.memory.knowledge import KnowledgeMemory
from buster.repository.indexer import RepositoryIndexer
from buster.workspace.dashboard import WorkspaceDashboard
from buster.apps.manager import ApplicationManager
from buster.voice.engine import VoiceEngine
from buster.vision.engine import VisionEngine
from buster.automation.engine import AutomationEngine
from buster.agents.team import AgentTeam
from buster.plugins.manager import PluginManager
from buster.hardware.manager import HardwareManager
from buster.diagnostics.manager import DiagnosticsManager
from buster.brain.providers.manager import AIProviderManager
from buster.brain.conversation import ConversationManager
from buster.brain.engine import BrainEngine
from buster.ui.main_window import MainWindow
from buster.ui.v9.v9_shell import V9MainWindow, FaceWindow

class BusterRuntime:
    def __init__(self):
        self.settings = Settings()
        self.settings.data_dir.mkdir(exist_ok=True)
        self.settings.logs_dir.mkdir(exist_ok=True)
        self.settings.screenshots_dir.mkdir(exist_ok=True)
        self.bus = EventBus()
        self.state = AppState()
        self.logger = Logger(self.settings.logs_dir)
        self.services = ServiceContainer()
        self.thread_pool = self.services.register("thread_pool", ThreadPool(max_workers=6))
        self.services.register("tasks", TaskScheduler(self.thread_pool))
        self.services.register("system", SystemMonitor())
        self.services.register("memory", MemoryEngine(self.settings.memory_db))
        self.services.register("knowledge", KnowledgeMemory())
        self.services.register("repo", RepositoryIndexer("."))
        self.services.register("apps", ApplicationManager(self.settings.app_cache_file))
        self.services.register("voice", VoiceEngine(self.settings.wake_word, self.bus))
        self.services.register("vision", VisionEngine(self.bus))
        self.services.register("automation", AutomationEngine(self.settings.screenshots_dir))
        self.services.register("agents", AgentTeam(self.bus))
        self.services.register("plugins", PluginManager())
        self.services.register("hardware", HardwareManager())
        self.services.register("conversation", ConversationManager())
        self.services.register("ai", AIProviderManager(self.settings.ai_config_file))
        self.services.register("service_manager", ServiceManager(self.services, self.thread_pool))
        self.services.register("performance", PerformanceMonitor(self.services, self.thread_pool))
        self.services.register("workspace", WorkspaceDashboard(self.services))
        self.services.register("diagnostics", DiagnosticsManager(self.services))
        self.services.register("brain", BrainEngine(self.services, self.bus, self.logger))
        self.services.get("plugins").load_builtin()

    def run(self):
        app = QApplication(sys.argv)
        app.setApplicationName(self.settings.app_name)

        USE_V9_UI = True

        if USE_V9_UI:
            window = V9MainWindow(
                services=self.services,
                settings=self.settings,
            )
            face = FaceWindow()
            face.show()
        else:
            window = MainWindow(self.settings, self.state, self.services, self.bus)

        window.show()
        sys.exit(app.exec())

def main():
    BusterRuntime().run()
