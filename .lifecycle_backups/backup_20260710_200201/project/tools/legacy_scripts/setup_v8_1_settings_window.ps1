@'
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QCheckBox, QLineEdit, QPushButton,
    QFileDialog
)

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Buster Settings")
        self.resize(520, 420)

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)

        tabs.addTab(self.general_tab(), "General")
        tabs.addTab(self.ai_tab(), "AI")
        tabs.addTab(self.voice_tab(), "Voice")
        tabs.addTab(self.folders_tab(), "Folders")
        tabs.addTab(self.updates_tab(), "Updates")

        buttons = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def general_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.always_top = QCheckBox("Always on top")
        self.always_top.setChecked(getattr(self.settings, "always_on_top", False))
        layout.addWidget(self.always_top)

        self.startup = QCheckBox("Start with Windows")
        layout.addWidget(self.startup)

        layout.addStretch()
        return w

    def ai_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Default AI Provider"))
        self.provider = QComboBox()
        self.provider.addItems(["local", "ollama", "lmstudio", "openrouter"])
        layout.addWidget(self.provider)

        layout.addStretch()
        return w

    def voice_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Wake Word"))
        self.wake_word = QLineEdit(getattr(self.settings, "wake_word", "hey buster"))
        layout.addWidget(self.wake_word)

        self.voice_enabled = QCheckBox("Enable voice")
        self.voice_enabled.setChecked(True)
        layout.addWidget(self.voice_enabled)

        layout.addStretch()
        return w

    def folders_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.data_dir = self.folder_row(layout, "Data folder", str(getattr(self.settings, "data_dir", "data")))
        self.logs_dir = self.folder_row(layout, "Logs folder", str(getattr(self.settings, "logs_dir", "logs")))
        self.screenshots_dir = self.folder_row(layout, "Screenshots folder", str(getattr(self.settings, "screenshots_dir", "screenshots")))

        layout.addStretch()
        return w

    def updates_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.check_updates = QCheckBox("Check for updates on startup")
        self.check_updates.setChecked(True)
        layout.addWidget(self.check_updates)

        layout.addWidget(QLabel("Updates use the GitHub Releases page."))
        layout.addStretch()
        return w

    def folder_row(self, layout, label, value):
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        box = QLineEdit(value)
        browse = QPushButton("Browse")

        def pick():
            folder = QFileDialog.getExistingDirectory(self, label, box.text())
            if folder:
                box.setText(folder)

        browse.clicked.connect(pick)
        row.addWidget(box)
        row.addWidget(browse)
        layout.addLayout(row)
        return box

    def get_values(self):
        return {
            "always_on_top": self.always_top.isChecked(),
            "wake_word": self.wake_word.text().strip(),
            "data_dir": self.data_dir.text().strip(),
            "logs_dir": self.logs_dir.text().strip(),
            "screenshots_dir": self.screenshots_dir.text().strip(),
            "check_updates": self.check_updates.isChecked(),
            "ai_provider": self.provider.currentText(),
            "voice_enabled": self.voice_enabled.isChecked(),
            "start_with_windows": self.startup.isChecked(),
        }
'@ | Set-Content "buster/ui/settings_dialog.py"

Write-Host "Settings dialog upgraded."