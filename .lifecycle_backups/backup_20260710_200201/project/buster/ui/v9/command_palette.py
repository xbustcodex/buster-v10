from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget
from buster.ui.v9.theme import STYLE

class CommandPalette(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.resize(520, 420)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type a command...")
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.addItems([
            "workspace snapshot",
            "git status",
            "python info",
            "approved folders",
            "repo summary",
            "index project",
            "check updates",
            "settings",
        ])
        layout.addWidget(self.list)

        self.search.textChanged.connect(self.filter)
        self.list.itemDoubleClicked.connect(self.accept)

    def filter(self, text):
        text = text.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text not in item.text().lower())

    def selected_command(self):
        item = self.list.currentItem()
        return item.text() if item else self.search.text().strip()
