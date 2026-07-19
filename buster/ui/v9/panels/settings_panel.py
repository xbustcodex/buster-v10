
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SettingsPanel(QWidget):
    settings_saved = Signal(dict)
    ai_provider_changed = Signal(str)

    PROVIDERS = {
        "OpenRouter": "openrouter",
        "Ollama": "ollama",
        "LM Studio": "lmstudio",
        "Local Rules": "local",
    }

    PROVIDER_LABELS = {
        value: key for key, value in PROVIDERS.items()
    }

    DEFAULT_MODELS = {
        "openrouter": "openai/gpt-4o-mini",
        "ollama": "qwen2.5-coder:3b",
        "lmstudio": "local-model",
        "local": "",
    }

    def __init__(self, live=None, runtime_core=None):
        super().__init__()

        self.live = live
        self.runtime_core = (
            runtime_core
            or getattr(live, "runtime_core", None)
        )
        self.ai_manager = self._resolve_ai_manager()

        self.config_path = Path.cwd() / "config" / "ui_settings.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.setObjectName("SettingsPanel")
        self.setWindowTitle("Buster Settings")
        self.resize(900, 720)

        self._build_ui()
        self._connect_signals()
        self._apply_styles()
        self.load()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)

        icon = QLabel("⚙")
        icon.setObjectName("HeaderIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(44, 44)

        heading = QVBoxLayout()
        heading.setSpacing(2)

        title = QLabel("Buster Settings")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Configure the AI runtime, interface, and companion features."
        )
        subtitle.setObjectName("MutedText")

        heading.addWidget(title)
        heading.addWidget(subtitle)

        self.runtime_badge = QLabel("Runtime checking…")
        self.runtime_badge.setObjectName("RuntimeBadge")
        self.runtime_badge.setAlignment(Qt.AlignCenter)
        self.runtime_badge.setMinimumWidth(150)

        header_layout.addWidget(icon)
        header_layout.addLayout(heading, 1)
        header_layout.addWidget(self.runtime_badge)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(14)

        content_layout.addWidget(self._build_ai_card())
        content_layout.addWidget(self._build_interface_card())
        content_layout.addWidget(self._build_companion_card())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        root.addWidget(self._build_footer())

    def _new_card(self, title_text, subtitle_text):
        card = QFrame()
        card.setObjectName("SettingsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 15, 16, 15)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("SectionTitle")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("MutedText")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return card, layout

    def _build_ai_card(self):
        card, layout = self._new_card(
            "AI Runtime",
            "Select the provider and model used by Buster."
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        self.ai_provider = QComboBox()
        self.ai_provider.addItems(list(self.PROVIDERS.keys()))
        self.ai_provider.setMinimumHeight(36)

        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("Model name")
        self.ai_model.setMinimumHeight(36)

        self.ai_status = QLabel("Not connected")
        self.ai_status.setObjectName("AIStatus")
        self.ai_status.setWordWrap(True)

        self.test_ai_button = QPushButton("Test Connection")
        self.test_ai_button.setObjectName("SecondaryButton")
        self.test_ai_button.setMinimumHeight(36)

        grid.addWidget(self._field_label("Provider"), 0, 0)
        grid.addWidget(self.ai_provider, 0, 1)
        grid.addWidget(self._field_label("Model"), 1, 0)
        grid.addWidget(self.ai_model, 1, 1)
        grid.addWidget(self._field_label("Status"), 2, 0)
        grid.addWidget(self.ai_status, 2, 1)
        grid.addWidget(self.test_ai_button, 3, 1, alignment=Qt.AlignLeft)

        layout.addLayout(grid)

        helper = QLabel(
            "OpenRouter uses an online API. Ollama and LM Studio use local "
            "models. Local Rules works without an external model."
        )
        helper.setObjectName("MutedText")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        return card

    def _build_interface_card(self):
        card, layout = self._new_card(
            "Interface",
            "Control Buster's appearance and development tools."
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light", "Cyber"])
        self.theme.setMinimumHeight(36)

        self.developer_mode = QCheckBox("Enable developer mode")
        self.backend_tools = QCheckBox("Show backend tools")

        grid.addWidget(self._field_label("Theme"), 0, 0)
        grid.addWidget(self.theme, 0, 1)
        grid.addWidget(self._field_label("Developer"), 1, 0)
        grid.addWidget(self.developer_mode, 1, 1)
        grid.addWidget(self._field_label("Tools"), 2, 0)
        grid.addWidget(self.backend_tools, 2, 1)

        layout.addLayout(grid)
        return card

    def _build_companion_card(self):
        card, layout = self._new_card(
            "Companion Features",
            "Enable Buster's face, voice, and vision systems."
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.face_popup = QCheckBox("Enable face popup")
        self.voice_enabled = QCheckBox("Enable voice")
        self.vision_enabled = QCheckBox("Enable vision")

        grid.addWidget(self.face_popup, 0, 0)
        grid.addWidget(self.voice_enabled, 0, 1)
        grid.addWidget(self.vision_enabled, 1, 0)

        layout.addLayout(grid)
        return card

    def _build_footer(self):
        footer = QFrame()
        footer.setObjectName("FooterCard")

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setObjectName("PrimaryButton")
        self.reload_button = QPushButton("Reload")
        self.reset_button = QPushButton("Reset Defaults")
        self.reset_button.setObjectName("DangerButton")

        for button in (
            self.save_button,
            self.reload_button,
            self.reset_button,
        ):
            button.setMinimumHeight(38)

        buttons.addWidget(self.save_button)
        buttons.addWidget(self.reload_button)
        buttons.addWidget(self.reset_button)
        buttons.addStretch()

        self.output = QTextEdit()
        self.output.setObjectName("SettingsOutput")
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(110)
        self.output.setMaximumHeight(165)

        layout.addLayout(buttons)
        layout.addWidget(self.output)

        return footer

    @staticmethod
    def _field_label(text):
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        label.setMinimumWidth(110)
        return label

    def _connect_signals(self):
        self.ai_provider.currentTextChanged.connect(
            self._provider_changed
        )
        self.test_ai_button.clicked.connect(
            self.test_ai_connection
        )
        self.save_button.clicked.connect(self.save)
        self.reload_button.clicked.connect(self.load)
        self.reset_button.clicked.connect(self.reset_defaults)

    # ------------------------------------------------------------------
    # AI integration
    # ------------------------------------------------------------------

    def _resolve_ai_manager(self):
        if self.runtime_core is not None:
            manager = getattr(self.runtime_core, "ai_manager", None)
            if manager is not None:
                return manager

            manager = getattr(
                self.runtime_core,
                "provider_manager",
                None,
            )
            if manager is not None:
                return manager

        if self.live is not None:
            manager = getattr(self.live, "ai_manager", None)
            if manager is not None:
                return manager

            legacy_service = getattr(
                self.live,
                "_legacy_service",
                None,
            )
            if callable(legacy_service):
                try:
                    return legacy_service("ai")
                except Exception:
                    pass

        return None

    def _selected_provider_key(self):
        return self.PROVIDERS.get(
            self.ai_provider.currentText(),
            "local",
        )

    def _provider_changed(self, _text):
        provider_key = self._selected_provider_key()
        current_model = self.ai_model.text().strip()

        known_models = {
            model for model in self.DEFAULT_MODELS.values() if model
        }

        if not current_model or current_model in known_models:
            self.ai_model.setText(
                self.DEFAULT_MODELS.get(provider_key, "")
            )

        self._refresh_ai_status(preview=True)

    def _apply_ai_runtime(self, provider_key, model_name):
        if self.ai_manager is None:
            return (
                "Settings saved, but no shared AIProviderManager "
                "is connected."
            )

        result = self.ai_manager.set_provider(provider_key)

        provider = getattr(
            self.ai_manager,
            "providers",
            {},
        ).get(provider_key)

        if provider is not None and model_name:
            if hasattr(provider, "preferred_model"):
                provider.preferred_model = model_name
            if hasattr(provider, "model"):
                provider.model = model_name

        return str(result)

    def _refresh_ai_status(self, preview=False):
        if self.ai_manager is None:
            self.runtime_badge.setText("Runtime unavailable")
            self.runtime_badge.setProperty("state", "offline")
            self.ai_status.setText(
                "No shared AIProviderManager is connected."
            )
            self._repolish(self.runtime_badge)
            return

        current_key = str(
            getattr(self.ai_manager, "current", "unknown")
        )
        selected_key = self._selected_provider_key()
        display_key = selected_key if preview else current_key

        provider_label = self.PROVIDER_LABELS.get(
            display_key,
            display_key.replace("_", " ").title(),
        )

        model_name = self.ai_model.text().strip()
        provider = getattr(
            self.ai_manager,
            "providers",
            {},
        ).get(display_key)

        if not preview and provider is not None:
            model_name = str(
                getattr(provider, "model", model_name) or model_name
            )

        if preview and selected_key != current_key:
            suffix = " · Save to activate"
        else:
            suffix = ""

        model_text = f" · {model_name}" if model_name else ""
        self.ai_status.setText(
            f"{provider_label}{model_text}{suffix}"
        )

        self.runtime_badge.setText("Runtime connected")
        self.runtime_badge.setProperty("state", "online")
        self._repolish(self.runtime_badge)

    def test_ai_connection(self):
        provider_key = self._selected_provider_key()
        model_name = self.ai_model.text().strip()

        if self.ai_manager is None:
            QMessageBox.warning(
                self,
                "AI Connection",
                "No shared AIProviderManager is connected.",
            )
            return

        try:
            provider = getattr(
                self.ai_manager,
                "providers",
                {},
            ).get(provider_key)

            if provider is None:
                raise RuntimeError(
                    f"Provider '{provider_key}' is not registered."
                )

            if model_name:
                if hasattr(provider, "preferred_model"):
                    provider.preferred_model = model_name
                if hasattr(provider, "model"):
                    provider.model = model_name

            available_fn = getattr(provider, "available", None)
            status_fn = getattr(provider, "status", None)

            available = (
                bool(available_fn())
                if callable(available_fn)
                else True
            )

            status_text = (
                str(status_fn())
                if callable(status_fn)
                else "No status information available."
            )

            display_name = self.PROVIDER_LABELS.get(
                provider_key,
                provider_key,
            )

            self.output.setPlainText(
                "AI CONNECTION TEST\n\n"
                f"Provider: {display_name}\n"
                f"Model: {model_name or 'Not required'}\n"
                f"Available: {'Yes' if available else 'No'}\n"
                f"Status: {status_text}"
            )

            if available:
                QMessageBox.information(
                    self,
                    "AI Connection",
                    f"{display_name} is available.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "AI Connection",
                    status_text,
                )

        except Exception as exc:
            self.output.setPlainText(
                f"AI connection test failed:\n\n{exc}"
            )
            QMessageBox.critical(
                self,
                "AI Connection Error",
                str(exc),
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def defaults(self) -> dict[str, Any]:
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
        provider_value = str(
            data.get("ai_provider", "OpenRouter")
        )

        if provider_value in self.PROVIDER_LABELS:
            provider_value = self.PROVIDER_LABELS[provider_value]

        provider_value = {
            "Local": "Local Rules",
            "Offline": "Local Rules",
        }.get(provider_value, provider_value)

        if provider_value not in self.PROVIDERS:
            provider_value = "OpenRouter"

        self.ai_provider.blockSignals(True)
        self.ai_provider.setCurrentText(provider_value)
        self.ai_provider.blockSignals(False)

        provider_key = self.PROVIDERS[provider_value]

        self.ai_model.setText(
            str(
                data.get(
                    "ai_model",
                    self.DEFAULT_MODELS.get(provider_key, ""),
                )
            )
        )
        self.theme.setCurrentText(
            str(data.get("theme", "Dark"))
        )
        self.developer_mode.setChecked(
            bool(data.get("developer_mode", True))
        )
        self.backend_tools.setChecked(
            bool(data.get("show_backend_tools", True))
        )
        self.face_popup.setChecked(
            bool(data.get("face_popup", True))
        )
        self.voice_enabled.setChecked(
            bool(data.get("voice_enabled", False))
        )
        self.vision_enabled.setChecked(
            bool(data.get("vision_enabled", False))
        )

    def load(self):
        data = self.defaults()
        note = ""

        if self.config_path.exists():
            try:
                stored = json.loads(
                    self.config_path.read_text(encoding="utf-8")
                )
                if isinstance(stored, dict):
                    data.update(stored)
            except (OSError, json.JSONDecodeError) as exc:
                note = f"\n\nLoad warning:\n{exc}"

        self.apply_values(data)
        self._refresh_ai_status()

        self.output.setPlainText(
            "SETTINGS LOADED\n\n"
            + json.dumps(data, indent=4)
            + f"\n\nPath:\n{self.config_path}"
            + note
        )

    def save(self):
        data = self.current_values()
        provider_key = self._selected_provider_key()
        model_name = data["ai_model"]

        if provider_key != "local" and not model_name:
            QMessageBox.warning(
                self,
                "Settings",
                "Enter a model name for the selected provider.",
            )
            return

        try:
            self.config_path.write_text(
                json.dumps(data, indent=4),
                encoding="utf-8",
            )

            runtime_result = self._apply_ai_runtime(
                provider_key,
                model_name,
            )

            self._refresh_ai_status()
            self.settings_saved.emit(dict(data))
            self.ai_provider_changed.emit(provider_key)

            self.output.setPlainText(
                "SETTINGS SAVED\n\n"
                + json.dumps(data, indent=4)
                + f"\n\nAI runtime:\n{runtime_result}"
                + f"\n\nPath:\n{self.config_path}"
            )

            QMessageBox.information(
                self,
                "Settings",
                "Settings saved and AI provider updated.",
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Settings Error",
                str(exc),
            )

    def reset_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        data = self.defaults()
        self.apply_values(data)

        try:
            self.config_path.write_text(
                json.dumps(data, indent=4),
                encoding="utf-8",
            )

            runtime_result = self._apply_ai_runtime(
                self._selected_provider_key(),
                self.ai_model.text().strip(),
            )

            self._refresh_ai_status()
            self.settings_saved.emit(dict(data))
            self.ai_provider_changed.emit(
                self._selected_provider_key()
            )

            self.output.setPlainText(
                "DEFAULTS RESTORED\n\n"
                + json.dumps(data, indent=4)
                + f"\n\nAI runtime:\n{runtime_result}"
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Settings Error",
                str(exc),
            )

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget#SettingsPanel {
                background: #0b1018;
                color: #e7edf6;
            }

            QFrame#HeaderCard,
            QFrame#SettingsCard,
            QFrame#FooterCard {
                background: #111925;
                border: 1px solid #243247;
                border-radius: 12px;
            }

            QLabel#HeaderIcon {
                background: #18263a;
                border: 1px solid #2f4869;
                border-radius: 10px;
                font-size: 21px;
            }

            QLabel#PageTitle {
                color: #f4f7fb;
                font-size: 22px;
                font-weight: 700;
            }

            QLabel#SectionTitle {
                color: #f0f4fa;
                font-size: 15px;
                font-weight: 700;
            }

            QLabel#MutedText {
                color: #8fa0b7;
                font-size: 12px;
            }

            QLabel#FieldLabel {
                color: #afbdd0;
                font-weight: 600;
            }

            QLabel#AIStatus {
                color: #9ec8ff;
                background: #0d1520;
                border: 1px solid #223149;
                border-radius: 7px;
                padding: 8px 10px;
            }

            QLabel#RuntimeBadge {
                color: #aab6c6;
                background: #151d29;
                border: 1px solid #2a3545;
                border-radius: 12px;
                padding: 7px 11px;
                font-weight: 600;
            }

            QLabel#RuntimeBadge[state="online"] {
                color: #9be5b2;
                background: #10251a;
                border-color: #215b38;
            }

            QLabel#RuntimeBadge[state="offline"] {
                color: #ffb4b4;
                background: #2b1719;
                border-color: #673236;
            }

            QComboBox,
            QLineEdit,
            QTextEdit {
                background: #0d1520;
                color: #e8edf5;
                border: 1px solid #27364b;
                border-radius: 7px;
                padding: 7px 9px;
                selection-background-color: #315985;
            }

            QComboBox:hover,
            QLineEdit:hover,
            QTextEdit:hover {
                border-color: #3b5271;
            }

            QComboBox:focus,
            QLineEdit:focus,
            QTextEdit:focus {
                border-color: #4f83bd;
            }

            QCheckBox {
                spacing: 9px;
                color: #d8e0eb;
                padding: 4px 0;
            }

            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                background: #0d1520;
                border: 1px solid #40516a;
                border-radius: 4px;
            }

            QCheckBox::indicator:checked {
                background: #3d74ad;
                border-color: #6094ca;
            }

            QPushButton {
                color: #dce6f3;
                background: #172231;
                border: 1px solid #2e4058;
                border-radius: 7px;
                padding: 8px 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #1c2b3e;
                border-color: #426184;
            }

            QPushButton#PrimaryButton {
                color: white;
                background: #2f68a3;
                border-color: #4c86c2;
            }

            QPushButton#DangerButton {
                color: #ffcbcb;
                background: #2a181c;
                border-color: #62333b;
            }

            QTextEdit#SettingsOutput {
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
            }

            QScrollArea {
                background: transparent;
                border: none;
            }
            """
        )

    @staticmethod
    def _repolish(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
