import sys
from PySide6.QtWidgets import QApplication

from buster.config.settings import Settings
from buster.core.events import EventBus
from buster.core.state import AppState
from buster.core.logger import Logger
from buster.core.container import ServiceContainer

from buster.services.thread_pool import ThreadPool
from buster.services.task_scheduler import TaskScheduler
from buster.ui.v9.main_window import V9MainWindow




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
        self.thread_pool = self.services.register(
            "thread_pool",
            ThreadPool(max_workers=6),
        )
        self.services.register(
            "tasks",
            TaskScheduler(self.thread_pool),
        )

    def run(self):
        app = QApplication(sys.argv)
        app.setApplicationName(self.settings.app_name)

        window = V9MainWindow(
            services=self.services,
            settings=self.settings,
        )
        window.show()

        sys.exit(app.exec())


def main():
    BusterRuntime().run()