from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication
from buster.ui.v9.theme import STYLE
from buster.ui.v9.live_services import V9LiveServices
from buster.ui.v9.sidebar import Sidebar
from buster.ui.v9.chat_view import ChatView
from buster.ui.v9.face_window import FaceWindow
from buster.ui.v9.dashboard import DashboardWindow
from buster.ui.v9.command_palette import CommandPalette

class V9MainWindow(QMainWindow):
    def __init__(self, services=None, settings=None):
        super().__init__()
        self.services = services
        self.settings = settings
        self.live = V9LiveServices(services, settings)
        self.face_window = None
        self.current_face_state = 'idle'
        self.dashboard_window = None

        self.setWindowTitle("Buster v9.0 — Windows AI Desktop Companion")
        self.resize(1280, 820)
        self.setStyleSheet(STYLE)
        self.build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_live)
        self.timer.start(2500)

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = Sidebar(self.live, self.show_dashboard, self.show_face)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(28, 22, 28, 18)

        title = QLabel("Buster Desktop AI OS\nYour AI Development Companion")
        title.setObjectName("Title")
        main_layout.addWidget(title)

        self.chat = ChatView(self.live, self.refresh_live, self.set_face_state)
        main_layout.addWidget(self.chat, 1)

        footer = QLabel("Context: buster-desktop-companion     Tokens: 1,248     Temp: 0.2")
        footer.setObjectName("Small")
        main_layout.addWidget(footer)

        outer.addWidget(self.sidebar)
        outer.addWidget(main, 1)

    def refresh_live(self):
        self.sidebar.refresh()

    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.set_state(self.current_face_state)
        self.face_window.show()
        self.face_window.raise_()

    def set_face_state(self, state):
        print("FACE STATE:", state)
        self.current_face_state = state

        if self.face_window is None:
            self.face_window = FaceWindow()
            self.face_window.show()

        self.face_window.set_state(state)
        self.face_window.raise_()
        QApplication.processEvents()

    def show_dashboard(self):
        if self.dashboard_window is None:
            self.dashboard_window = DashboardWindow(self.live)
        self.dashboard_window.show()
        self.dashboard_window.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_K and event.modifiers() & Qt.ControlModifier:
            dlg = CommandPalette(self)
            if dlg.exec():
                cmd = dlg.selected_command()
                if cmd:
                    self.chat.input.setText(cmd)
                    self.chat.send()
            return

        super().keyPressEvent(event)
