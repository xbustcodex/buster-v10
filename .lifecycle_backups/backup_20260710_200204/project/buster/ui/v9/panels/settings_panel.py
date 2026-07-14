import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QMessageBox,
)


class SettingsPanel(QWidget):
    def __init__(self, live=None):
        super().__init__()
        self.live = live
        self.config_path = Path.cwd() / "config" / "ui_settings.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("Settings")
        self.resize(820, 640)

        layout = QVBoxLayout(self)

        title = QLabel("⚙ Settings")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.ai_provider = QComboBox()
        self.ai_provider.addItems(["OpenRouter", "Local", "Ollama", "Offline"])

        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("Model name")

        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light", "Cyber"])

        self.developer_mode = QCheckBox("Developer Mode")
        self.backend_tools = QCheckBox("Show Backend Tools")
        self.face_popup = QCheckBox("Enable Face Popup")
        self.voice_enabled = QCheckBox("Enable Voice")
        self.vision_enabled = QCheckBox("Enable Vision")

        form_items = [
            ("AI Provider", self.ai_provider),
            ("AI Model", self.ai_model),
            ("Theme", self.theme),
            ("Developer Mode", self.developer_mode),
            ("Backend Tools", self.backend_tools),
            ("Face Popup", self.face_popup),
            ("Voice", self.voice_enabled),
            ("Vision", self.vision_enabled),
        ]

        for label_text, widget in form_items:
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(160)
            row.addWidget(label)
            row.addWidget(widget, 1)
            layout.addLayout(row)

        buttons = QHBoxLayout()

        save = QPushButton("Save")
        save.clicked.connect(self.save)

        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self.load)

        reset = QPushButton("Reset Defaults")
        reset.clicked.connect(self.reset_defaults)

        buttons.addWidget(save)
        buttons.addWidget(reload_btn)
        buttons.addWidget(reset)
        buttons.addStretch()

        layout.addLayout(buttons)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        self.load()

    def defaults(self):
        return {
            "ai_provider": "OpenRouter",
            "ai_model": "openai/gpt-4o-mini",
            "theme": "Dark",
            "developer_mode": True,
            "show_backend_tools": True,
            "face_popup": True,
            "voice_enabled": False,
            "vision_enabled": False,
        }

    def current_values(self):
        return {
            "ai_provider": self.ai_provider.currentText(),
            "ai_model": self.ai_model.text().strip(),
            "theme": self.theme.currentText(),
            "developer_mode": self.developer_mode.isChecked(),
            "show_backend_tools": self.backend_tools.isChecked(),
            "face_popup": self.face_popup.isChecked(),
            "voice_enabled": self.voice_enabled.isChecked(),
            "vision_enabled": self.vision_enabled.isChecked(),
        }

    def apply_values(self, data):
        self.ai_provider.setCurrentText(data.get("ai_provider", "OpenRouter"))
        self.ai_model.setText(data.get("ai_model", "openai/gpt-4o-mini"))
        self.theme.setCurrentText(data.get("theme", "Dark"))
        self.developer_mode.setChecked(bool(data.get("developer_mode", True)))
        self.backend_tools.setChecked(bool(data.get("show_backend_tools", True)))
        self.face_popup.setChecked(bool(data.get("face_popup", True)))
        self.voice_enabled.setChecked(bool(data.get("voice_enabled", False)))
        self.vision_enabled.setChecked(bool(data.get("vision_enabled", False)))

    def load(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                data = self.defaults()
        else:
            data = self.defaults()

        self.apply_values(data)
        self.output.setPlainText(
            "Loaded settings:\n\n"
            + json.dumps(data, indent=4)
            + f"\n\nPath:\n{self.config_path}"
        )

    def save(self):
        data = self.current_values()
        self.config_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
        self.output.setPlainText(
            "Saved settings:\n\n"
            + json.dumps(data, indent=4)
            + f"\n\nPath:\n{self.config_path}"
        )
        QMessageBox.information(self, "Settings", "Settings saved.")

    def reset_defaults(self):
        data = self.defaults()
        self.apply_values(data)
        self.config_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
        self.output.setPlainText("Reset to defaults:\n\n" + json.dumps(data, indent=4))