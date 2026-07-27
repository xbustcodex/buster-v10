from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(slots=True)
class ComponentState:
    task: str
    status: str
    health: str
    detail: str
    complete: bool
    operational: bool = False
    action: str = "Review"


class AsyncTestRunner(QThread):
    """Run a callable without blocking the checklist UI."""

    finished_signal = Signal(object)

    def __init__(self, check_func: Callable[[], Any], parent=None):
        super().__init__(parent)
        self.check_func = check_func

    def run(self) -> None:
        try:
            self.finished_signal.emit(self.check_func())
        except Exception as exc:
            self.finished_signal.emit(
                {"_error": f"Background operation failed: {exc}"}
            )


class InstalledComponentScanner(QThread):
    """Inspect Buster services, providers and local modules."""

    scan_finished = Signal(dict)

    def __init__(self, panel: "DeveloperChecklistPanel"):
        super().__init__(panel)
        self.panel = panel

    def run(self) -> None:
        try:
            result = self.panel.detect_installed_components()
        except Exception as exc:
            result = {
                "_error": f"Installed component scan failed: {exc}"
            }
        self.scan_finished.emit(result)


class DeveloperChecklistPanel(QWidget):
    """
    Live Buster capability checklist and remediation control panel.

    The panel distinguishes implementation from operational readiness:

    - Running: active and usable now.
    - Installed: implementation or dependency exists but is idle.
    - Configured: ready to use but not currently active.
    - Not Configured: implementation exists but required setup is missing.
    - Not Installed: implementation or dependency was not detected.
    - Blocked: a required dependency is incomplete.
    - Error: a component exists but failed health inspection.
    """

    repair_plan_requested = Signal(dict)
    component_action_requested = Signal(dict)

    STATUS_RUNNING = "✅ Running"
    STATUS_INSTALLED = "🔵 Installed"
    STATUS_CONFIGURED = "🟡 Configured"
    STATUS_NOT_CONFIGURED = "🟠 Not Configured"
    STATUS_NOT_INSTALLED = "⚪ Not Installed"
    STATUS_BLOCKED = "⛔ Blocked"
    STATUS_ERROR = "🔴 Error"
    STATUS_DONE = "✅ Done"
    STATUS_PENDING = "⚪ Pending"

    HEALTH_HEALTHY = "Healthy"
    HEALTH_READY = "Ready"
    HEALTH_IDLE = "Idle"
    HEALTH_BLOCKED = "Blocked"
    HEALTH_FAILED = "Failed"
    HEALTH_UNKNOWN = "Unknown"

    COMPLETE_STATES = {
        STATUS_RUNNING,
        STATUS_INSTALLED,
        STATUS_CONFIGURED,
        STATUS_DONE,
    }

    STATUS_COLOURS = {
        STATUS_RUNNING: "#2E7D32",
        STATUS_INSTALLED: "#1565C0",
        STATUS_CONFIGURED: "#F9A825",
        STATUS_NOT_CONFIGURED: "#EF6C00",
        STATUS_NOT_INSTALLED: "#757575",
        STATUS_BLOCKED: "#6A1B9A",
        STATUS_ERROR: "#C62828",
        STATUS_DONE: "#2E7D32",
        STATUS_PENDING: "#757575",
    }

    HEALTH_COLOURS = {
        HEALTH_HEALTHY: "#2E7D32",
        HEALTH_READY: "#F9A825",
        HEALTH_IDLE: "#1565C0",
        HEALTH_BLOCKED: "#6A1B9A",
        HEALTH_FAILED: "#C62828",
        HEALTH_UNKNOWN: "#757575",
    }

    REMOTE_PROVIDER_KEYS = {
        "OpenRouter": (
            "OPENROUTER_API_KEY",
            "OPEN_ROUTER_API_KEY",
        ),
        "Claude": (
            "ANTHROPIC_API_KEY",
            "CLAUDE_API_KEY",
        ),
        "OpenAI": ("OPENAI_API_KEY",),
        "Gemini": (
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENERATIVE_AI_API_KEY",
        ),
    }

    LOCAL_PROVIDERS = {
        "Ollama",
        "LM Studio",
        "llama.cpp",
    }

    DEPENDENCIES = {
        "Local Whisper STT": ("PyAudio Input",),
        "Voice Activity Detection": ("PyAudio Input",),
        "Streaming STT": (
            "PyAudio Input",
            "Local Whisper STT",
            "Voice Activity Detection",
        ),
        "Wake-Word Engine": (
            "PyAudio Input",
            "Voice Activity Detection",
        ),
        "Edge-TTS": (),
        "AI conversation verified": (
            "Provider Framework",
        ),
        "Self Improvement verified": (
            "Self Improvement Service",
            "Execution Engine",
        ),
        "Execution Engine verified": (
            "Execution Engine",
        ),
        "Plugin loading verified": (),
    }

    CHECKLIST_DATA = {
        "UI COMPLETION": [
            ("Dashboard", True),
            ("Chat", True),
            ("Sidebar Navigation", True),
            ("Runtime Workspace", True),
            ("Runtime Timeline", True),
            ("Face Popup", True),
            ("Notification Center", True),
            ("Developer Mission Control", True),
            ("Self Improvement", True),
        ],
        "AUDIO & VOICE ENGINE": [
            ("PyAudio Input", True),
            ("Google Speech Recognition", True),
            ("Local Whisper STT", False),
            ("Edge-TTS", False),
            ("pyttsx3 Fallback", True),
            ("Wake-Word Engine", False),
            ("Voice Activity Detection", False),
            ("Streaming STT", False),
        ],
        "CORE RUNTIME": [
            ("Runtime Core", True),
            ("Event Bus", True),
            ("Service Manager", True),
            ("Runtime Monitor", True),
            ("Lifecycle Manager", True),
        ],
        "AI INTEGRATION": [
            ("Provider Framework", True),
            ("Ollama", True),
            ("LM Studio", False),
            ("llama.cpp", False),
            ("OpenRouter", False),
            ("Claude", False),
            ("OpenAI", False),
            ("Gemini", False),
        ],
        "AUTONOMY": [
            ("Autonomy Engine", True),
            ("Execution Engine", True),
            ("Self Improvement Service", True),
            ("Strategy Selector", True),
            ("Risk Analysis", True),
        ],
        "SYSTEM TESTING": [
            ("UI opens without errors", False),
            ("Runtime starts cleanly", False),
            ("Event Bus verified", False),
            ("All panels refresh", False),
            ("Memory verified", False),
            ("Plugin loading verified", False),
            ("AI conversation verified", False),
            ("Execution Engine verified", False),
            ("Self Improvement verified", False),
        ],
        "RELEASE PREPARATION": [
            ("PyInstaller build", False),
            ("Installer", False),
            ("Documentation", False),
        ],
    }

    def __init__(self, live=None, runtime_core=None, parent=None):
        super().__init__(parent)
        self.live = live
        self.runtime_core = (
            runtime_core
            or getattr(live, "kernel_core", None)
            or getattr(live, "runtime_core", None)
            or getattr(live, "core", None)
        )

        self.worker: Optional[AsyncTestRunner] = None
        self.install_scanner: Optional[InstalledComponentScanner] = None
        self._component_states: dict[str, ComponentState] = {}
        self._auto_detected_tasks: set[str] = set()

        self.init_ui()
        self.populate_checklist()

        self.auto_scan_timer = QTimer(self)
        self.auto_scan_timer.setInterval(10000)
        self.auto_scan_timer.timeout.connect(
            self.scan_installed_components
        )
        self.auto_scan_timer.start()

        QTimer.singleShot(0, self.scan_installed_components)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def init_ui(self) -> None:
        self.setWindowTitle("Developer Checklist")
        self.resize(1080, 760)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("🛠 Buster Developer Checklist")
        title.setStyleSheet(
            "font-size:18px;font-weight:800;margin-bottom:2px;"
        )
        layout.addWidget(title)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "font-weight:700;color:#2E7D32;margin-bottom:2px;"
        )
        layout.addWidget(self.status_label)

        self.state_legend = QLabel(
            "✅ Running · 🔵 Installed · 🟡 Configured · "
            "🟠 Not Configured · ⚪ Not Installed · "
            "⛔ Blocked · 🔴 Error"
        )
        self.state_legend.setWordWrap(True)
        self.state_legend.setStyleSheet(
            "color:#546E7A;font-size:10px;margin-bottom:4px;"
        )
        layout.addWidget(self.state_legend)

        splitter = QSplitter(Qt.Vertical)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            [
                "Task / Component",
                "Status",
                "Health",
                "Details / Required Action",
            ]
        )
        self.tree.header().setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )
        self.tree.header().setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents,
        )
        self.tree.header().setSectionResizeMode(
            2,
            QHeaderView.ResizeToContents,
        )
        self.tree.header().setSectionResizeMode(
            3,
            QHeaderView.Stretch,
        )
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.currentItemChanged.connect(
            self._on_current_item_changed
        )
        splitter.addWidget(self.tree)

        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 6, 0, 0)
        lower_layout.setSpacing(6)

        self.selection_label = QLabel(
            "Select a component to inspect or repair."
        )
        self.selection_label.setWordWrap(True)
        self.selection_label.setStyleSheet(
            "font-weight:700;color:#37474F;"
        )
        lower_layout.addWidget(self.selection_label)

        component_actions = QHBoxLayout()
        self.fix_selected_btn = QPushButton("Fix Selected")
        self.fix_selected_btn.setEnabled(False)
        self.fix_selected_btn.clicked.connect(
            self.fix_selected_component
        )

        self.generate_plan_btn = QPushButton(
            "Generate Repair Plan"
        )
        self.generate_plan_btn.clicked.connect(
            self.generate_missing_components_plan
        )

        self.fix_missing_btn = QPushButton(
            "Fix Missing Components"
        )
        self.fix_missing_btn.clicked.connect(
            self.fix_missing_components
        )

        component_actions.addWidget(self.fix_selected_btn)
        component_actions.addWidget(self.generate_plan_btn)
        component_actions.addWidget(self.fix_missing_btn)
        component_actions.addStretch()
        lower_layout.addLayout(component_actions)

        add_layout = QHBoxLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.setPlaceholderText(
            "Select or type category..."
        )
        self.cat_combo.setMinimumWidth(210)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText(
            "Enter new task name..."
        )
        self.task_input.returnPressed.connect(
            self.add_item_from_ui
        )

        add_btn = QPushButton("➕ Add Task")
        add_btn.clicked.connect(self.add_item_from_ui)

        add_layout.addWidget(self.cat_combo)
        add_layout.addWidget(self.task_input, 1)
        add_layout.addWidget(add_btn)
        lower_layout.addLayout(add_layout)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(125)
        self.log_console.setFont(QFont("Consolas", 9))
        self.log_console.setPlaceholderText(
            "Detection, verification and repair-plan logs..."
        )
        lower_layout.addWidget(self.log_console)

        buttons_layout = QHBoxLayout()
        actions = [
            ("Check All", lambda: self.toggle_all(True)),
            ("Uncheck All", lambda: self.toggle_all(False)),
            ("Scan Installed", self.scan_installed_components),
            ("Run Quick Verification", self.run_quick_checks),
            ("Copy Checklist", self.copy_to_clipboard),
            ("Reset Default", self.populate_checklist),
        ]

        for label, callback in actions:
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons_layout.addWidget(button)

        buttons_layout.addStretch()
        lower_layout.addLayout(buttons_layout)

        splitter.addWidget(lower)
        splitter.setSizes([520, 220])
        layout.addWidget(splitter, 1)

    # ------------------------------------------------------------------
    # Checklist population
    # ------------------------------------------------------------------

    def populate_checklist(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self.cat_combo.clear()
        self._component_states.clear()

        for category, items in self.CHECKLIST_DATA.items():
            self.cat_combo.addItem(category)

            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, category)
            category_item.setFlags(
                category_item.flags()
                | Qt.ItemFlag.ItemIsAutoTristate
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            category_item.setFont(
                0,
                QFont("Segoe UI", 10, QFont.Bold),
            )

            for task_name, is_checked in items:
                child = QTreeWidgetItem(category_item)
                child.setText(0, task_name)
                child.setFlags(
                    child.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                )

                status = (
                    self.STATUS_DONE
                    if is_checked
                    else self.STATUS_PENDING
                )
                health = (
                    self.HEALTH_HEALTHY
                    if is_checked
                    else self.HEALTH_UNKNOWN
                )
                self._set_item_state(
                    child,
                    ComponentState(
                        task=task_name,
                        status=status,
                        health=health,
                        detail=(
                            "Marked complete in the default checklist."
                            if is_checked
                            else "Awaiting automatic inspection."
                        ),
                        complete=is_checked,
                        operational=is_checked,
                        action="Review",
                    ),
                    source="manual",
                )

            category_item.setExpanded(True)

        self.tree.blockSignals(False)
        self.update_summary()

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan_installed_components(self) -> None:
        if self.install_scanner and self.install_scanner.isRunning():
            return

        self.log_console.append(
            "[Scanner] Inspecting runtime services, providers, "
            "dependencies and component health..."
        )

        self.install_scanner = InstalledComponentScanner(self)
        self.install_scanner.scan_finished.connect(
            self.apply_installed_component_results
        )
        self.install_scanner.start()

    def detect_installed_components(
        self,
    ) -> dict[str, dict[str, Any]]:
        states: dict[str, ComponentState] = {}
        runtime = self._runtime_core()
        services = self._service_registry(runtime)
        providers = self._provider_objects(runtime, services)

        def put(state: ComponentState) -> None:
            states[state.task.lower()] = state

        runtime_components = {
            "Dashboard": (
                "buster.ui.v9.dashboard",
                ("dashboard",),
            ),
            "Chat": (
                "buster.ui.v9.chat_view",
                ("chat", "chat_service"),
            ),
            "Sidebar Navigation": (
                "buster.ui.v9.sidebar",
                ("sidebar",),
            ),
            "Runtime Workspace": (
                "buster.ui.v9.panels.runtime_panel.runtime_workspace",
                ("runtime_workspace",),
            ),
            "Runtime Timeline": (
                "buster.ui.v9.panels.runtime_panel.runtime_timeline_panel",
                ("runtime_monitor", "timeline"),
            ),
            "Face Popup": (
                "buster.ui.v9.face_window",
                ("face", "face_window"),
            ),
            "Notification Center": (
                "buster.ui.v9.panels.notification_center_panel",
                ("notifications", "notification_center"),
            ),
            "Developer Mission Control": (
                "buster.ui.v9.panels.developer_mission_control",
                ("developer_mission_control",),
            ),
            "Self Improvement": (
                "buster.ui.v9.panels.self_improvement_panel",
                ("self_improvement", "self_improvement_service"),
            ),
            "Runtime Core": (
                "buster.runtime.core",
                ("runtime", "runtime_core"),
            ),
            "Event Bus": (
                "buster.runtime.dispatcher",
                ("event_bus", "event_router", "dispatcher"),
            ),
            "Service Manager": (
                "buster.runtime.services",
                ("services", "service_manager"),
            ),
            "Runtime Monitor": (
                "buster.ui.v9.runtime_monitor",
                ("runtime_monitor",),
            ),
            "Lifecycle Manager": (
                "buster.lifecycle",
                ("lifecycle", "lifecycle_manager"),
            ),
            "Autonomy Engine": (
                "buster.autonomy",
                ("autonomy", "autonomy_engine"),
            ),
            "Execution Engine": (
                "buster.execution",
                ("execution", "execution_engine"),
            ),
            "Self Improvement Service": (
                "buster.self_improvement.self_improvement_service",
                ("self_improvement_service",),
            ),
            "Strategy Selector": (
                "buster.autonomy",
                ("strategy_selector",),
            ),
            "Risk Analysis": (
                "buster.autonomy",
                ("risk_analysis", "risk_analyzer"),
            ),
        }

        for task, (module_name, aliases) in runtime_components.items():
            runtime_match = self._find_runtime_alias(
                runtime,
                services,
                aliases,
            )
            if runtime_match:
                put(
                    ComponentState(
                        task,
                        self.STATUS_RUNNING,
                        self.HEALTH_HEALTHY,
                        runtime_match,
                        True,
                        True,
                        "Open",
                    )
                )
            elif self._module_available(module_name):
                put(
                    ComponentState(
                        task,
                        self.STATUS_INSTALLED,
                        self.HEALTH_IDLE,
                        f"Built-in module detected: {module_name}",
                        True,
                        False,
                        "Start",
                    )
                )
            else:
                put(
                    ComponentState(
                        task,
                        self.STATUS_NOT_INSTALLED,
                        self.HEALTH_UNKNOWN,
                        f"Missing module or service: {module_name}",
                        False,
                        False,
                        "Install",
                    )
                )

        dependency_checks = {
            "PyAudio Input": ("pyaudio",),
            "Google Speech Recognition": ("speech_recognition",),
            "Local Whisper STT": ("faster_whisper", "whisper"),
            "Edge-TTS": ("edge_tts",),
            "pyttsx3 Fallback": ("pyttsx3",),
            "Voice Activity Detection": (
                "webrtcvad",
                "silero_vad",
            ),
        }

        audio_aliases = {
            "PyAudio Input": (
                "pyaudio",
                "audio_input",
                "microphone",
            ),
            "Google Speech Recognition": (
                "speech_recognition",
                "google_speech",
            ),
            "Local Whisper STT": (
                "whisper",
                "faster_whisper",
                "local_stt",
                "stt",
            ),
            "Edge-TTS": (
                "edge_tts",
                "tts",
                "speech_synthesis",
            ),
            "pyttsx3 Fallback": (
                "pyttsx3",
                "offline_tts",
            ),
            "Wake-Word Engine": (
                "wake_word",
                "wakeword",
                "porcupine",
                "keyword_spotter",
            ),
            "Voice Activity Detection": (
                "vad",
                "voice_activity_detection",
            ),
            "Streaming STT": (
                "streaming_stt",
                "speech_stream",
                "streaming_transcription",
            ),
        }

        for task, aliases in audio_aliases.items():
            runtime_match = self._find_runtime_alias(
                runtime,
                services,
                aliases,
            )
            if runtime_match:
                put(
                    ComponentState(
                        task,
                        self.STATUS_RUNNING,
                        self.HEALTH_HEALTHY,
                        runtime_match,
                        True,
                        True,
                        "Open",
                    )
                )
                continue

            dependency = next(
                (
                    name
                    for name in dependency_checks.get(task, ())
                    if self._module_available(name)
                ),
                None,
            )
            if dependency:
                put(
                    ComponentState(
                        task,
                        self.STATUS_INSTALLED,
                        self.HEALTH_IDLE,
                        f"Python dependency detected: {dependency}. "
                        "No active Buster service was found.",
                        True,
                        False,
                        "Integrate",
                    )
                )
            else:
                put(
                    ComponentState(
                        task,
                        self.STATUS_NOT_INSTALLED,
                        self.HEALTH_UNKNOWN,
                        self._missing_audio_reason(task),
                        False,
                        False,
                        "Install",
                    )
                )

        provider_framework_found = (
            self._module_available("buster.ai")
            or self._module_available("buster.providers")
            or bool(providers)
        )
        put(
            ComponentState(
                "Provider Framework",
                (
                    self.STATUS_INSTALLED
                    if provider_framework_found
                    else self.STATUS_NOT_INSTALLED
                ),
                (
                    self.HEALTH_READY
                    if provider_framework_found
                    else self.HEALTH_UNKNOWN
                ),
                (
                    "Buster provider registry detected."
                    if provider_framework_found
                    else "Provider registry was not detected."
                ),
                provider_framework_found,
                False,
                "Open" if provider_framework_found else "Install",
            )
        )

        provider_aliases = {
            "Ollama": ("ollama",),
            "LM Studio": ("lmstudio", "lm_studio"),
            "llama.cpp": (
                "llama_cpp",
                "llamacpp",
                "llama.cpp",
            ),
            "OpenRouter": ("openrouter", "open_router"),
            "Claude": ("claude", "anthropic"),
            "OpenAI": ("openai",),
            "Gemini": ("gemini", "google"),
        }

        for task, aliases in provider_aliases.items():
            provider_name, provider = self._match_provider(
                providers,
                aliases,
            )

            if provider_name is not None:
                runtime_state = self._provider_runtime_state(provider)

                if runtime_state["error"]:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_ERROR,
                            self.HEALTH_FAILED,
                            runtime_state["evidence"],
                            False,
                            False,
                            "Repair",
                        )
                    )
                    continue

                # Buster's own provider reports are authoritative. If the
                # provider is ready/running, credentials may be stored in
                # Buster's encrypted settings rather than environment vars.
                if runtime_state["running"]:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_RUNNING,
                            self.HEALTH_HEALTHY,
                            f"Buster provider '{provider_name}' is usable. "
                            f"{runtime_state['evidence']}",
                            True,
                            True,
                            "Open",
                        )
                    )
                    continue

                if runtime_state["configured"]:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_CONFIGURED,
                            self.HEALTH_READY,
                            f"Buster provider '{provider_name}' reports "
                            "usable configuration.",
                            True,
                            False,
                            "Start",
                        )
                    )
                    continue

                credential = self._provider_credential_evidence(
                    task,
                    provider,
                )
                if credential:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_CONFIGURED,
                            self.HEALTH_READY,
                            f"Provider '{provider_name}' registered; "
                            f"{credential}.",
                            True,
                            False,
                            "Test",
                        )
                    )
                else:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_NOT_CONFIGURED,
                            self.HEALTH_BLOCKED,
                            f"Provider '{provider_name}' is installed but "
                            "Buster did not report it ready.",
                            False,
                            False,
                            "Configure",
                        )
                    )
                continue

            dependency = next(
                (
                    alias
                    for alias in aliases
                    if "." not in alias
                    and self._module_available(alias)
                ),
                None,
            )

            if dependency:
                if task in self.REMOTE_PROVIDER_KEYS:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_NOT_CONFIGURED,
                            self.HEALTH_BLOCKED,
                            f"SDK '{dependency}' exists, but no usable "
                            "Buster provider was registered.",
                            False,
                            False,
                            "Configure",
                        )
                    )
                else:
                    put(
                        ComponentState(
                            task,
                            self.STATUS_INSTALLED,
                            self.HEALTH_IDLE,
                            f"Dependency detected: {dependency}.",
                            True,
                            False,
                            "Integrate",
                        )
                    )
            else:
                put(
                    ComponentState(
                        task,
                        self.STATUS_NOT_INSTALLED,
                        self.HEALTH_UNKNOWN,
                        "Provider and dependency were not detected.",
                        False,
                        False,
                        "Install",
                    )
                )

        self._apply_dependency_blocks(states)

        return {
            key: {
                "task": state.task,
                "status": state.status,
                "health": state.health,
                "detail": state.detail,
                "complete": state.complete,
                "operational": state.operational,
                "action": state.action,
            }
            for key, state in states.items()
        }

    def _apply_dependency_blocks(
        self,
        states: dict[str, ComponentState],
    ) -> None:
        for task, dependencies in self.DEPENDENCIES.items():
            key = task.lower()
            state = states.get(key)
            if state is None or state.complete:
                continue

            missing = []
            for dependency in dependencies:
                dependency_state = states.get(dependency.lower())
                if dependency_state is None or not dependency_state.complete:
                    missing.append(dependency)

            if missing:
                state.status = self.STATUS_BLOCKED
                state.health = self.HEALTH_BLOCKED
                state.detail = (
                    "Blocked by incomplete dependencies: "
                    + ", ".join(missing)
                )
                state.action = "Fix Dependencies"

    @staticmethod
    def _missing_audio_reason(task: str) -> str:
        reasons = {
            "Local Whisper STT": (
                "Faster-Whisper or Whisper is not installed and no "
                "local STT service is registered."
            ),
            "Edge-TTS": (
                "The edge-tts dependency and Edge-TTS service are missing."
            ),
            "Wake-Word Engine": (
                "No wake-word or keyword-spotting service is registered."
            ),
            "Voice Activity Detection": (
                "No WebRTC VAD, Silero VAD or Buster VAD service detected."
            ),
            "Streaming STT": (
                "No streaming transcription service is registered."
            ),
        }
        return reasons.get(
            task,
            "Required dependency or runtime service was not detected.",
        )

    # ------------------------------------------------------------------
    # Applying scan results
    # ------------------------------------------------------------------

    def apply_installed_component_results(
        self,
        results: dict,
    ) -> None:
        error = results.pop("_error", None)
        if error:
            self.log_console.append(f"[Scanner Error] {error}")
            return

        complete = 0
        incomplete = 0

        self.tree.blockSignals(True)
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                category = root.child(i)
                for j in range(category.childCount()):
                    item = category.child(j)
                    task_key = item.text(0).strip().lower()
                    raw = results.get(task_key)
                    if raw is None:
                        continue

                    state = ComponentState(
                        task=raw["task"],
                        status=raw["status"],
                        health=raw["health"],
                        detail=raw["detail"],
                        complete=bool(raw["complete"]),
                        operational=bool(raw["operational"]),
                        action=raw["action"],
                    )
                    self._set_item_state(
                        item,
                        state,
                        source="auto",
                    )

                    if state.complete:
                        self._auto_detected_tasks.add(task_key)
                        complete += 1
                    else:
                        self._auto_detected_tasks.discard(task_key)
                        incomplete += 1
        finally:
            self.tree.blockSignals(False)

        self.update_summary()
        self._update_selected_component_panel()
        self.log_console.append(
            f"[Scanner] {complete} implemented · "
            f"{incomplete} missing, blocked, unconfigured or failed."
        )

    # ------------------------------------------------------------------
    # State rendering and progress
    # ------------------------------------------------------------------

    def _set_item_state(
        self,
        item: QTreeWidgetItem,
        state: ComponentState,
        source: str,
    ) -> None:
        self._component_states[state.task.lower()] = state

        item.setCheckState(
            0,
            (
                Qt.CheckState.Checked
                if state.complete
                else Qt.CheckState.Unchecked
            ),
        )
        item.setText(1, state.status)
        item.setText(2, state.health)
        item.setText(3, state.detail)
        item.setData(0, Qt.ItemDataRole.UserRole, source)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, state.action)

        item.setForeground(
            1,
            QBrush(
                QColor(
                    self.STATUS_COLOURS.get(
                        state.status,
                        "#424242",
                    )
                )
            ),
        )
        item.setForeground(
            2,
            QBrush(
                QColor(
                    self.HEALTH_COLOURS.get(
                        state.health,
                        "#424242",
                    )
                )
            ),
        )

        tooltip = (
            f"Status: {state.status}\n"
            f"Health: {state.health}\n"
            f"Action: {state.action}\n"
            f"Details: {state.detail}"
        )
        for column in range(4):
            item.setToolTip(column, tooltip)

    def update_summary(self) -> None:
        total = 0
        implemented = 0
        operational = 0
        operational_candidates = 0
        status_counts = {
            self.STATUS_RUNNING: 0,
            self.STATUS_INSTALLED: 0,
            self.STATUS_CONFIGURED: 0,
            self.STATUS_NOT_CONFIGURED: 0,
            self.STATUS_NOT_INSTALLED: 0,
            self.STATUS_BLOCKED: 0,
            self.STATUS_ERROR: 0,
        }

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            category = root.child(i)
            for j in range(category.childCount()):
                item = category.child(j)
                total += 1
                state = self._component_states.get(
                    item.text(0).strip().lower()
                )

                if state is None:
                    if item.checkState(0) == Qt.CheckState.Checked:
                        implemented += 1
                    continue

                if state.complete:
                    implemented += 1

                if state.status in {
                    self.STATUS_RUNNING,
                    self.STATUS_CONFIGURED,
                    self.STATUS_INSTALLED,
                }:
                    operational_candidates += 1
                    if state.operational:
                        operational += 1

                if state.status in status_counts:
                    status_counts[state.status] += 1

        implementation_pct = (
            implemented / total * 100
            if total
            else 0.0
        )
        operational_pct = (
            operational / operational_candidates * 100
            if operational_candidates
            else 0.0
        )

        self.status_label.setText(
            f"Branch: {self.get_git_branch()}  |  "
            f"Implementation: {implemented}/{total} "
            f"({implementation_pct:.1f}%)  |  "
            f"Operational: {operational}/{operational_candidates} "
            f"({operational_pct:.1f}%)  |  "
            f"Running {status_counts[self.STATUS_RUNNING]} · "
            f"Installed {status_counts[self.STATUS_INSTALLED]} · "
            f"Configured {status_counts[self.STATUS_CONFIGURED]} · "
            f"Blocked {status_counts[self.STATUS_BLOCKED]} · "
            f"Errors {status_counts[self.STATUS_ERROR]}"
        )

    # ------------------------------------------------------------------
    # Selection and remediation workflows
    # ------------------------------------------------------------------

    def _on_current_item_changed(
        self,
        current: Optional[QTreeWidgetItem],
        previous: Optional[QTreeWidgetItem],
    ) -> None:
        del previous
        self._update_selected_component_panel(current)

    def _update_selected_component_panel(
        self,
        item: Optional[QTreeWidgetItem] = None,
    ) -> None:
        item = item or self.tree.currentItem()
        if item is None or item.childCount() > 0:
            self.selection_label.setText(
                "Select a component to inspect or repair."
            )
            self.fix_selected_btn.setEnabled(False)
            return

        task = item.text(0)
        state = self._component_states.get(task.lower())
        if state is None:
            self.selection_label.setText(task)
            self.fix_selected_btn.setEnabled(True)
            self.fix_selected_btn.setText("Review Selected")
            return

        self.selection_label.setText(
            f"{task} — {state.status} / {state.health}\n"
            f"{state.detail}"
        )
        self.fix_selected_btn.setText(state.action)
        self.fix_selected_btn.setEnabled(
            state.action not in {"Open", "Review"}
            or not state.complete
        )

    def fix_selected_component(self) -> None:
        item = self.tree.currentItem()
        if item is None or item.childCount() > 0:
            return

        task = item.text(0)
        state = self._component_states.get(task.lower())
        if state is None:
            return

        request = self._build_component_request(state)
        self.component_action_requested.emit(request)

        if self._submit_to_self_improvement(request):
            self.log_console.append(
                f"[Self Improvement] Submitted: {task}"
            )
            QMessageBox.information(
                self,
                "Component Submitted",
                f"{task} was submitted to Buster's "
                "Self Improvement workflow for review.",
            )
        else:
            self.log_console.append(
                f"[Repair Request] {request['instruction']}"
            )
            QMessageBox.information(
                self,
                "Repair Request Prepared",
                "No compatible Self Improvement submission method was "
                "exposed. The repair request has been written to the log "
                "and emitted through component_action_requested.",
            )

    def generate_missing_components_plan(self) -> None:
        missing = self._missing_states()
        if not missing:
            QMessageBox.information(
                self,
                "Repair Plan",
                "No missing, blocked, unconfigured or failed "
                "components were found.",
            )
            return

        plan = self._build_repair_plan(missing)
        self.repair_plan_requested.emit(plan)

        self.log_console.append(
            "=== GENERATED CAPABILITY REPAIR PLAN ==="
        )
        self.log_console.append(plan["summary"])
        for index, step in enumerate(plan["steps"], 1):
            self.log_console.append(
                f"{index}. {step['task']} — {step['action']} — "
                f"{step['reason']}"
            )

        QMessageBox.information(
            self,
            "Repair Plan Generated",
            f"Prepared a {len(plan['steps'])}-step plan.\n\n"
            "The plan has been emitted through repair_plan_requested "
            "and written to the checklist log.",
        )

    def fix_missing_components(self) -> None:
        missing = self._missing_states()
        if not missing:
            QMessageBox.information(
                self,
                "Fix Missing Components",
                "No missing components were found.",
            )
            return

        plan = self._build_repair_plan(missing)

        confirmation = QMessageBox.question(
            self,
            "Fix Missing Components",
            f"Submit {len(plan['steps'])} capability tasks to "
            "Buster's Self Improvement workflow?\n\n"
            "This prepares reviewed repair work. It does not bypass "
            "Buster's approval, transaction or verification gates.",
        )
        if confirmation != QMessageBox.Yes:
            return

        submitted = 0
        for state in missing:
            request = self._build_component_request(state)
            if self._submit_to_self_improvement(request):
                submitted += 1
            self.component_action_requested.emit(request)

        self.repair_plan_requested.emit(plan)
        self.log_console.append(
            f"[Self Improvement] Submitted {submitted}/"
            f"{len(missing)} tasks through a compatible runtime method."
        )

        QMessageBox.information(
            self,
            "Missing Components",
            f"Prepared {len(missing)} capability tasks.\n"
            f"Directly submitted: {submitted}\n\n"
            "All requests were emitted for Mission Control or another "
            "integration layer to consume.",
        )

    def _missing_states(self) -> list[ComponentState]:
        return [
            state
            for state in self._component_states.values()
            if state.status
            in {
                self.STATUS_NOT_CONFIGURED,
                self.STATUS_NOT_INSTALLED,
                self.STATUS_BLOCKED,
                self.STATUS_ERROR,
                self.STATUS_PENDING,
            }
        ]

    def _build_component_request(
        self,
        state: ComponentState,
    ) -> dict[str, Any]:
        dependencies = list(
            self.DEPENDENCIES.get(state.task, ())
        )
        return {
            "source": "developer_checklist",
            "task": state.task,
            "status": state.status,
            "health": state.health,
            "action": state.action,
            "reason": state.detail,
            "dependencies": dependencies,
            "instruction": (
                f"Bring the Buster capability '{state.task}' to a "
                "verified usable state. "
                f"Current status: {state.status}. "
                f"Current health: {state.health}. "
                f"Reason: {state.detail}. "
                "Use Buster's normal review, preview, transaction, "
                "verification and rollback gates."
            ),
        }

    def _build_repair_plan(
        self,
        states: list[ComponentState],
    ) -> dict[str, Any]:
        priority_order = {
            "PyAudio Input": 10,
            "Voice Activity Detection": 20,
            "Local Whisper STT": 30,
            "Streaming STT": 40,
            "Edge-TTS": 50,
            "Wake-Word Engine": 60,
            "Provider Framework": 70,
            "llama.cpp": 80,
            "Claude": 90,
            "Gemini": 100,
        }

        ordered = sorted(
            states,
            key=lambda state: (
                priority_order.get(state.task, 500),
                state.task.lower(),
            ),
        )

        steps = [
            {
                "task": state.task,
                "action": state.action,
                "reason": state.detail,
                "dependencies": list(
                    self.DEPENDENCIES.get(state.task, ())
                ),
            }
            for state in ordered
        ]

        return {
            "source": "developer_checklist",
            "title": "Buster Capability Completion Plan",
            "summary": (
                f"{len(steps)} incomplete capability item(s) found. "
                "Audio foundations are prioritized before dependent "
                "voice features, followed by AI providers and release work."
            ),
            "steps": steps,
        }

    def _submit_to_self_improvement(
        self,
        request: dict[str, Any],
    ) -> bool:
        candidates = []

        for owner in (
            self.runtime_core,
            self.live,
        ):
            if owner is None:
                continue

            for name in (
                "self_improvement_service",
                "self_improvement",
                "repair_service",
            ):
                value = getattr(owner, name, None)
                if value is not None:
                    candidates.append(value)

            services = getattr(owner, "services", None)
            if services is not None:
                for name in (
                    "self_improvement_service",
                    "self_improvement",
                    "repair_service",
                ):
                    value = self._lookup_service(services, name)
                    if value is not None:
                        candidates.append(value)

        for service in candidates:
            for method_name in (
                "submit_request",
                "create_request",
                "create_repair",
                "plan_repair",
                "run_repair",
                "start",
            ):
                method = getattr(service, method_name, None)
                if not callable(method):
                    continue

                for args in (
                    (request,),
                    (request["instruction"],),
                    (
                        request["task"],
                        request["instruction"],
                    ),
                ):
                    try:
                        method(*args)
                        return True
                    except TypeError:
                        continue
                    except Exception as exc:
                        self.log_console.append(
                            f"[Submission Error] {method_name}: {exc}"
                        )
                        break

        return self._publish_runtime_event(
            "developer_checklist.repair_requested",
            request,
        )

    def _publish_runtime_event(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        runtime = self._runtime_core()
        if runtime is None:
            return False

        for owner_name in (
            "event_bus",
            "event_router",
            "dispatcher",
            "router",
        ):
            owner = getattr(runtime, owner_name, None)
            if owner is None:
                continue

            for method_name in (
                "publish",
                "emit",
                "dispatch",
            ):
                method = getattr(owner, method_name, None)
                if not callable(method):
                    continue

                for args in (
                    (event_type, payload),
                    (
                        {
                            "type": event_type,
                            "payload": payload,
                        },
                    ),
                ):
                    try:
                        method(*args)
                        return True
                    except TypeError:
                        continue
                    except Exception:
                        return False
        return False

    # ------------------------------------------------------------------
    # Runtime/provider discovery helpers
    # ------------------------------------------------------------------

    def _runtime_core(self) -> Any:
        if self.runtime_core is not None:
            return self.runtime_core
        if self.live is None:
            return None
        return (
            getattr(self.live, "kernel_core", None)
            or getattr(self.live, "runtime_core", None)
            or getattr(self.live, "core", None)
            or self.live
        )

    @staticmethod
    def _service_registry(runtime: Any) -> Any:
        if runtime is None:
            return None
        return (
            getattr(runtime, "services", None)
            or getattr(runtime, "service_manager", None)
            or getattr(runtime, "registry", None)
        )

    @staticmethod
    def _registered_service_names(
        services: Any,
    ) -> set[str]:
        names: set[str] = set()
        if services is None:
            return names

        if isinstance(services, dict):
            names.update(str(key) for key in services)
            return names

        for attribute in (
            "_services",
            "services",
            "_registry",
            "registry",
        ):
            value = getattr(services, attribute, None)
            if isinstance(value, dict):
                names.update(str(key) for key in value)

        for method_name in (
            "list_services",
            "names",
            "keys",
            "all",
        ):
            method = getattr(services, method_name, None)
            if not callable(method):
                continue
            try:
                value = method()
            except Exception:
                continue

            if isinstance(value, dict):
                names.update(str(key) for key in value)
            elif isinstance(value, (list, tuple, set)):
                names.update(str(item) for item in value)

        return names

    def _provider_objects(
        self,
        runtime: Any,
        services: Any,
    ) -> dict[str, Any]:
        providers: dict[str, Any] = {}
        candidates: list[Any] = []

        for owner in (runtime, self.live):
            if owner is None:
                continue
            for attribute in (
                "providers",
                "provider_registry",
                "ai_providers",
                "model_providers",
            ):
                value = getattr(owner, attribute, None)
                if value is not None:
                    candidates.append(value)

        if services is not None:
            for name in (
                "providers",
                "provider_registry",
                "ai",
                "llm",
            ):
                value = self._lookup_service(services, name)
                if value is not None:
                    candidates.append(value)

        for candidate in candidates:
            if isinstance(candidate, dict):
                providers.update(
                    {
                        str(key): value
                        for key, value in candidate.items()
                    }
                )
                continue

            for attribute in (
                "_providers",
                "providers",
                "_registry",
                "registry",
            ):
                value = getattr(candidate, attribute, None)
                if isinstance(value, dict):
                    providers.update(
                        {
                            str(key): item
                            for key, item in value.items()
                        }
                    )

            for method_name in (
                "list_providers",
                "available_providers",
                "all",
            ):
                method = getattr(candidate, method_name, None)
                if not callable(method):
                    continue
                try:
                    value = method()
                except Exception:
                    continue

                if isinstance(value, dict):
                    providers.update(
                        {
                            str(key): item
                            for key, item in value.items()
                        }
                    )
                elif isinstance(value, (list, tuple, set)):
                    for item in value:
                        if isinstance(item, str):
                            providers.setdefault(item, None)
                        else:
                            name = (
                                getattr(item, "name", None)
                                or getattr(
                                    item,
                                    "provider_name",
                                    None,
                                )
                                or type(item).__name__
                            )
                            providers[str(name)] = item

        return providers

    @staticmethod
    def _match_provider(
        providers: dict[str, Any],
        aliases: tuple[str, ...],
    ) -> tuple[Optional[str], Any]:
        for name, provider in providers.items():
            normalized = (
                name.lower()
                .replace("-", "_")
                .replace(" ", "_")
            )
            if any(
                alias.lower() in normalized
                for alias in aliases
            ):
                return name, provider
        return None, None

    def _provider_runtime_state(
        self,
        provider: Any,
    ) -> dict[str, Any]:
        state = {
            "running": False,
            "configured": False,
            "error": False,
            "evidence": "Provider object detected.",
        }

        # Registry entries may expose a provider name only. A string entry
        # means it is registered, but not enough evidence to say running.
        if provider is None or isinstance(provider, str):
            return state

        for attribute in (
            "error",
            "last_error",
            "load_error",
        ):
            value = getattr(provider, attribute, None)
            if value:
                state["error"] = True
                state["evidence"] = f"{attribute}: {value}"
                return state

        for method_name in (
            "health",
            "status",
            "get_status",
            "quick_status",
        ):
            method = getattr(provider, method_name, None)
            if not callable(method):
                continue

            try:
                value = method()
            except Exception as exc:
                state["error"] = True
                state["evidence"] = (
                    f"{method_name} failed: {exc}"
                )
                return state

            status_text = ""
            if isinstance(value, dict):
                status_text = str(
                    value.get("status")
                    or value.get("state")
                    or value.get("message")
                    or ""
                ).lower()
                if value.get("configured") is True:
                    state["configured"] = True
                if value.get("available") is True:
                    state["running"] = True
                    state["configured"] = True
            elif isinstance(value, str):
                status_text = value.lower()
            elif value is True:
                status_text = "ready"

            if any(
                token in status_text
                for token in (
                    "error",
                    "failed",
                    "unavailable",
                    "offline",
                )
            ):
                state["error"] = True
                state["evidence"] = (
                    f"{method_name}: {status_text}"
                )
                return state

            if any(
                token in status_text
                for token in (
                    "running",
                    "ready",
                    "healthy",
                    "online",
                    "connected",
                    "available",
                )
            ):
                state["running"] = True
                state["configured"] = True
                state["evidence"] = (
                    f"{method_name}: {status_text}"
                )

        for attribute in (
            "running",
            "is_running",
            "ready",
            "is_ready",
            "healthy",
            "available",
            "is_available",
            "connected",
            "is_connected",
        ):
            value = getattr(provider, attribute, None)
            try:
                value = value() if callable(value) else value
            except Exception:
                continue
            if value is True:
                state["running"] = True
                state["configured"] = True
                state["evidence"] = f"{attribute}=True"

        for attribute in (
            "configured",
            "is_configured",
            "enabled",
        ):
            value = getattr(provider, attribute, None)
            try:
                value = value() if callable(value) else value
            except Exception:
                continue
            if value is True:
                state["configured"] = True

        return state

    def _provider_credential_evidence(
        self,
        task: str,
        provider: Any,
    ) -> Optional[str]:
        for environment_name in self.REMOTE_PROVIDER_KEYS.get(
            task,
            (),
        ):
            if os.getenv(environment_name, "").strip():
                return f"credential: {environment_name}"

        if provider is None:
            return None

        for attribute in (
            "api_key",
            "_api_key",
            "token",
            "_token",
            "credential",
            "credentials",
        ):
            value = getattr(provider, attribute, None)
            if isinstance(value, str) and value.strip():
                return f"provider credential: {attribute}"
            if value not in (
                None,
                False,
                "",
                {},
                [],
            ):
                return f"provider credential: {attribute}"

        config = getattr(provider, "config", None)
        if isinstance(config, dict):
            for key in (
                "api_key",
                "token",
                "credential",
                "credentials",
            ):
                if config.get(key):
                    return f"provider config: {key}"

        return None

    def _find_runtime_alias(
        self,
        runtime: Any,
        services: Any,
        aliases: tuple[str, ...],
    ) -> Optional[str]:
        normalized_aliases = {
            alias.lower()
            .replace("-", "_")
            .replace(" ", "_")
            for alias in aliases
        }

        if runtime is not None:
            for alias in normalized_aliases:
                value = getattr(runtime, alias, None)
                if value is not None:
                    return f"runtime.{alias}"

        for service_name in self._registered_service_names(
            services
        ):
            normalized_name = (
                service_name.lower()
                .replace("-", "_")
                .replace(" ", "_")
            )
            if any(
                alias in normalized_name
                or normalized_name in alias
                for alias in normalized_aliases
            ):
                service = self._lookup_service(
                    services,
                    service_name,
                )
                service_state = self._generic_service_state(service)
                return (
                    f"service: {service_name}"
                    + (
                        f" ({service_state})"
                        if service_state
                        else ""
                    )
                )

        for alias in aliases:
            service = self._lookup_service(services, alias)
            if service is not None:
                state = self._generic_service_state(service)
                return (
                    f"service: {alias}"
                    + (f" ({state})" if state else "")
                )

        return None

    @staticmethod
    def _generic_service_state(service: Any) -> str:
        if service is None:
            return ""

        for method_name in (
            "status",
            "get_status",
            "quick_status",
        ):
            method = getattr(service, method_name, None)
            if callable(method):
                try:
                    value = method()
                except Exception:
                    continue
                if isinstance(value, dict):
                    return str(
                        value.get("status")
                        or value.get("state")
                        or ""
                    )
                if value is not None:
                    return str(value)

        for attribute in (
            "running",
            "ready",
            "enabled",
        ):
            value = getattr(service, attribute, None)
            try:
                value = value() if callable(value) else value
            except Exception:
                continue
            if value is True:
                return attribute

        return ""

    @staticmethod
    def _lookup_service(
        services: Any,
        name: str,
    ) -> Any:
        if services is None:
            return None
        if isinstance(services, dict):
            return services.get(name)

        for method_name in (
            "get",
            "resolve",
            "service",
        ):
            method = getattr(services, method_name, None)
            if not callable(method):
                continue
            try:
                value = method(name)
            except Exception:
                continue
            if value is not None:
                return value

        return getattr(services, name, None)

    @staticmethod
    def _module_available(module_name: str) -> bool:
        try:
            return (
                importlib.util.find_spec(module_name)
                is not None
            )
        except (
            ImportError,
            AttributeError,
            ValueError,
        ):
            return False

    # ------------------------------------------------------------------
    # Manual checklist actions
    # ------------------------------------------------------------------

    def add_checklist_item(
        self,
        category_name: str,
        item_name: str,
        is_checked: bool = False,
    ) -> None:
        if not category_name.strip() or not item_name.strip():
            return

        category_name = category_name.strip().upper()
        item_name = item_name.strip()

        self.tree.blockSignals(True)
        try:
            root = self.tree.invisibleRootItem()
            category_item = None

            for index in range(root.childCount()):
                candidate = root.child(index)
                if candidate.text(0).upper() == category_name:
                    category_item = candidate
                    break

            if category_item is None:
                category_item = QTreeWidgetItem(self.tree)
                category_item.setText(0, category_name)
                category_item.setFlags(
                    category_item.flags()
                    | Qt.ItemFlag.ItemIsAutoTristate
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                category_item.setFont(
                    0,
                    QFont("Segoe UI", 10, QFont.Bold),
                )
                category_item.setExpanded(True)
                self.cat_combo.addItem(category_name)

            child = QTreeWidgetItem(category_item)
            child.setText(0, item_name)
            child.setFlags(
                child.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            self._set_item_state(
                child,
                ComponentState(
                    task=item_name,
                    status=(
                        self.STATUS_DONE
                        if is_checked
                        else self.STATUS_PENDING
                    ),
                    health=(
                        self.HEALTH_HEALTHY
                        if is_checked
                        else self.HEALTH_UNKNOWN
                    ),
                    detail=(
                        "Manually marked complete."
                        if is_checked
                        else "Manually added task."
                    ),
                    complete=is_checked,
                    operational=is_checked,
                    action="Review",
                ),
                source="manual",
            )
        finally:
            self.tree.blockSignals(False)

        self.update_summary()
        self.log_console.append(
            f"[Added] {item_name} under [{category_name}]"
        )

    def add_item_from_ui(self) -> None:
        category = self.cat_combo.currentText()
        task_name = self.task_input.text()
        if task_name.strip():
            self.add_checklist_item(
                category,
                task_name,
                is_checked=False,
            )
            self.task_input.clear()

    def on_item_changed(
        self,
        item: QTreeWidgetItem,
        column: int,
    ) -> None:
        if column != 0 or item.childCount() != 0:
            return

        source = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )
        task = item.text(0)
        current = self._component_states.get(task.lower())

        if source == "auto" and current is not None:
            expected = (
                Qt.CheckState.Checked
                if current.complete
                else Qt.CheckState.Unchecked
            )
            if item.checkState(0) != expected:
                item.setCheckState(0, expected)
        else:
            checked = (
                item.checkState(0)
                == Qt.CheckState.Checked
            )
            self._set_item_state(
                item,
                ComponentState(
                    task=task,
                    status=(
                        self.STATUS_DONE
                        if checked
                        else self.STATUS_PENDING
                    ),
                    health=(
                        self.HEALTH_HEALTHY
                        if checked
                        else self.HEALTH_UNKNOWN
                    ),
                    detail=(
                        "Manually marked complete."
                        if checked
                        else "Pending manual work."
                    ),
                    complete=checked,
                    operational=checked,
                    action="Review",
                ),
                source="manual",
            )

        self.update_summary()

    def toggle_all(self, check_state: bool) -> None:
        self.tree.blockSignals(True)
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                category = root.child(i)
                for j in range(category.childCount()):
                    item = category.child(j)
                    task = item.text(0)
                    self._set_item_state(
                        item,
                        ComponentState(
                            task=task,
                            status=(
                                self.STATUS_DONE
                                if check_state
                                else self.STATUS_PENDING
                            ),
                            health=(
                                self.HEALTH_HEALTHY
                                if check_state
                                else self.HEALTH_UNKNOWN
                            ),
                            detail=(
                                "Manually marked complete."
                                if check_state
                                else "Pending manual work."
                            ),
                            complete=check_state,
                            operational=check_state,
                            action="Review",
                        ),
                        source="manual",
                    )
        finally:
            self.tree.blockSignals(False)

        self.update_summary()

    # ------------------------------------------------------------------
    # Verification and export
    # ------------------------------------------------------------------

    def run_quick_checks(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        self.log_console.append(
            "=== RUNNING DIAGNOSTIC VERIFICATION ==="
        )

        def perform_checks() -> str:
            runtime = self._runtime_core()
            checks = [
                (
                    "✓ Runtime loaded"
                    if runtime is not None
                    else "✗ Runtime unavailable"
                )
            ]

            event_bus = None
            if runtime is not None:
                event_bus = (
                    getattr(runtime, "event_bus", None)
                    or getattr(runtime, "event_router", None)
                    or getattr(runtime, "dispatcher", None)
                )

            checks.append(
                (
                    "✓ Event bus responsive"
                    if event_bus is not None
                    else "✗ Event bus unavailable"
                )
            )

            states = self.detect_installed_components()
            checks.append(
                f"✓ {len(states)} component states inspected"
            )
            return "\n".join(checks)

        self.worker = AsyncTestRunner(perform_checks, self)
        self.worker.finished_signal.connect(
            self._handle_quick_check_result
        )
        self.worker.start()

    def _handle_quick_check_result(
        self,
        result: Any,
    ) -> None:
        if isinstance(result, dict) and "_error" in result:
            self.log_console.append(
                f"[Verification Error] {result['_error']}"
            )
            return

        self.log_console.append(
            f"{result}\n[Verification Completed]\n"
        )

    def copy_to_clipboard(self) -> None:
        output = (
            "## Buster Developer Checklist\n"
            f"**Git Branch:** {self.get_git_branch()}\n\n"
        )

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            category = root.child(i)
            output += f"### {category.text(0)}\n"

            for j in range(category.childCount()):
                item = category.child(j)
                checked = (
                    item.checkState(0)
                    == Qt.CheckState.Checked
                )
                box = "[x]" if checked else "[ ]"
                output += (
                    f"- {box} {item.text(0)} — "
                    f"{item.text(1)} — {item.text(2)} — "
                    f"{item.text(3)}\n"
                )
            output += "\n"

        QGuiApplication.clipboard().setText(output)
        self.log_console.append(
            "[System] Detailed checklist copied to clipboard."
        )

    def get_git_branch(self) -> str:
        if self.live and hasattr(self.live, "git_branch"):
            try:
                return str(self.live.git_branch())
            except Exception:
                pass
        return "main"

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self.auto_scan_timer.stop()

        for worker in (
            self.worker,
            self.install_scanner,
        ):
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                worker.wait(1000)

        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeveloperChecklistPanel()
    window.show()
    sys.exit(app.exec())
