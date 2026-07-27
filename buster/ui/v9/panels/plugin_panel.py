"""
Buster Plugin Manager & Hot-Patch Hub.

Responsibilities
----------------
- Discover plugins from the live runtime and local plugin directories.
- Show plugin status, metadata, commands, dependencies, permissions and health.
- Start, stop, reload, enable and disable plugins through runtime adapters.
- Keep the existing AST-assisted hot-patch drop workflow as a dedicated tab.
- Publish and display plugin lifecycle events without owning the runtime.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import logging
import os
import py_compile
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PluginRecord:
    """Normalized plugin information from runtime or filesystem discovery."""

    key: str
    name: str
    status: str = "Unknown"
    version: str = "—"
    description: str = ""
    author: str = "—"
    module_name: str = ""
    path: Optional[Path] = None
    commands: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    health: str = "Unknown"
    enabled: bool = True
    source: str = "runtime"
    raw: Any = None


class SmartDropZone(QFrame):
    """Drag-and-drop target with AST-assisted destination routing."""

    file_dropped = Signal(str, str)

    def __init__(self, project_root: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.project_root = (project_root or Path.cwd()).resolve()
        self.setAcceptDrops(True)
        self.setObjectName("SmartDropZone")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(150)
        self.setStyleSheet(
            """
            QFrame#SmartDropZone {
                background:#0A1726;
                border:2px dashed #2878B8;
                border-radius:12px;
                padding:20px;
            }
            QFrame#SmartDropZone:hover {
                border-color:#23B8FF;
                background:#10253A;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("📥")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:34px;background:transparent;")

        self.text_label = QLabel(
            "Drop a Python component or plugin here\n"
            "or click to browse"
        )
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet(
            "color:#DCEBFF;font-size:13px;font-weight:700;"
            "background:transparent;"
        )

        hint = QLabel("AST routing · syntax preflight · backup · live reload")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            "color:#8FA9C4;font-size:10px;background:transparent;"
        )

        layout.addWidget(icon)
        layout.addWidget(self.text_label)
        layout.addWidget(hint)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                target = self._analyze_and_route(file_path)
                self.file_dropped.emit(file_path, target)
        event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Plugin or Component",
            "",
            "Python Files (*.py);;All Files (*)",
        )
        if file_path:
            self.file_dropped.emit(
                file_path,
                self._analyze_and_route(file_path),
            )

    def _analyze_and_route(self, file_path: str) -> str:
        path = Path(file_path)
        filename = path.name

        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            return f"buster/plugins/{filename}"

        lowered = content.lower()
        class_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }

        if (
            "plugin" in filename.lower()
            or any(name.endswith("Plugin") for name in class_names)
            or "plugin_manifest" in lowered
        ):
            return f"buster/plugins/{filename}"

        if any(
            marker in content
            for marker in (
                "Blackboard",
                "TaskDelegator",
                "GrowthLedger",
                "CuriosityEngine",
            )
        ):
            return f"buster/brain/{filename}"

        if any(
            marker in lowered
            for marker in (
                "playwright",
                "pyautogui",
                "desktopautomation",
                "browserautomation",
            )
        ):
            return f"buster/automation/{filename}"

        if any(
            marker in content
            for marker in (
                "EventRouter",
                "EventBus",
                "ServiceRegistry",
                "SandboxManager",
                "SecurityIntercept",
            )
        ):
            return f"buster/kernel/{filename}"

        imports_pyside = any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            and "PySide6" in ast.unparse(node)
            for node in ast.walk(tree)
        )
        if imports_pyside or filename.endswith("_panel.py"):
            return f"buster/ui/v9/panels/{filename}"

        if any(
            name.endswith(("Service", "Manager", "Engine", "Router"))
            for name in class_names
        ):
            return f"buster/runtime/{filename}"

        if any(name.endswith("Agent") for name in class_names):
            return f"buster/agents/{filename}"

        return f"buster/plugins/{filename}"


class PluginPanel(QWidget):
    """Live Plugin Manager with a separate hot-patch workspace."""

    plugin_selected = Signal(str)
    plugin_action_completed = Signal(str, str)

    def __init__(self, runtime_core=None, live=None, parent=None):
        super().__init__(parent)
        self.runtime_core = runtime_core
        self.live = live
        self.project_root = Path.cwd().resolve()

        self._records: dict[str, PluginRecord] = {}
        self._selected_key: Optional[str] = None
        self._selected_patch_file: Optional[Path] = None
        self._target_rel_path: Optional[str] = None
        self._suggested_target_rel_path: Optional[str] = None
        self._override_target_dir: Optional[str] = None
        self._override_buttons: dict[str, QPushButton] = {}
        self._event_unsubscribers: list[Callable[[], None]] = []
        self._command_owners: dict[str, str] = {}
        self._runtime_commands: dict[str, Any] = {}

        self.setObjectName("PluginPanel")
        self._build_ui()
        self._connect_runtime_events()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.refresh_plugins)
        self.refresh_timer.start()

        QTimer.singleShot(0, self.refresh_plugins)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget#PluginPanel {
                background:#0B1726;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }
            QGroupBox {
                color:#CFE1F4;
                border:1px solid #244560;
                border-radius:8px;
                margin-top:9px;
                padding-top:8px;
                font-weight:700;
            }
            QGroupBox::title {
                subcontrol-origin:margin;
                left:10px;
                padding:0 5px;
            }
            QPushButton {
                background:#17334E;
                color:#E8F2FC;
                border:1px solid #2B587B;
                border-radius:6px;
                padding:6px 11px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#204B70;
                border-color:#23B8FF;
                color:#FFFFFF;
            }
            QPushButton:checked {
                background:#20527A;
                color:#FFFFFF;
                border:1px solid #23B8FF;
            }
            QPushButton:disabled {
                background:#142536;
                color:#60758A;
                border-color:#24394C;
            }
            QLineEdit, QPlainTextEdit, QListWidget, QTableWidget {
                background:#0E1D2E;
                color:#DCEBFF;
                border:1px solid #244560;
                border-radius:6px;
                selection-background-color:#20527A;
            }
            QHeaderView::section {
                background:#17334E;
                color:#DCEBFF;
                border:0;
                border-right:1px solid #244560;
                border-bottom:1px solid #244560;
                padding:6px;
                font-weight:700;
            }
            QTabWidget::pane {
                border:1px solid #244560;
                border-radius:7px;
                background:#0B1726;
            }
            QTabBar::tab {
                background:#10253A;
                color:#9EB6CF;
                border:1px solid #244560;
                padding:7px 14px;
                margin-right:2px;
            }
            QTabBar::tab:selected {
                background:#20527A;
                color:#FFFFFF;
                border-color:#23B8FF;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        header = QHBoxLayout()

        title_box = QVBoxLayout()
        title = QLabel("PLUGIN MANAGER")
        title.setStyleSheet(
            "color:#23B8FF;font-size:21px;font-weight:900;"
            "letter-spacing:1px;background:transparent;"
        )
        subtitle = QLabel(
            "Live discovery · lifecycle controls · commands · health · hot patch"
        )
        subtitle.setStyleSheet(
            "color:#9EB6CF;font-size:11px;background:transparent;"
        )
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.runtime_status = QLabel("● Runtime unavailable")
        self.runtime_status.setStyleSheet(
            "color:#FFB000;font-weight:700;background:transparent;"
        )
        header.addWidget(self.runtime_status)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_plugins)
        header.addWidget(self.refresh_btn)

        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_installed_tab(), "Installed")
        self.tabs.addTab(self._build_hotpatch_tab(), "Hot Patch")
        self.tabs.addTab(self._build_commands_tab(), "Commands")
        self.tabs.addTab(self._build_events_tab(), "Events")
        root.addWidget(self.tabs, 1)

    def _build_installed_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Filter:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search plugins, status, commands or module..."
        )
        self.search_box.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_box, 1)

        self.summary_label = QLabel("0 plugins")
        self.summary_label.setStyleSheet(
            "color:#9EB6CF;font-weight:700;background:transparent;"
        )
        search_row.addWidget(self.summary_label)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Horizontal)

        self.plugin_table = QTableWidget(0, 5)
        self.plugin_table.setHorizontalHeaderLabels(
            ["Plugin", "Status", "Version", "Health", "Source"]
        )
        self.plugin_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.plugin_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.plugin_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.plugin_table.verticalHeader().setVisible(False)
        self.plugin_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )
        for column in range(1, 5):
            self.plugin_table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )
        self.plugin_table.itemSelectionChanged.connect(
            self._on_table_selection
        )
        splitter.addWidget(self.plugin_table)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(8, 0, 0, 0)

        self.detail_title = QLabel("Select a plugin")
        self.detail_title.setStyleSheet(
            "color:#23B8FF;font-size:18px;font-weight:800;"
            "background:transparent;"
        )
        detail_layout.addWidget(self.detail_title)

        self.detail_text = QPlainTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText(
            "Plugin details will appear here."
        )
        detail_layout.addWidget(self.detail_text, 1)

        action_grid = QGridLayout()

        self.start_btn = self._action_button(
            "Start",
            lambda: self._perform_action("start"),
        )
        self.stop_btn = self._action_button(
            "Stop",
            lambda: self._perform_action("stop"),
        )
        self.reload_btn = self._action_button(
            "Reload",
            lambda: self._perform_action("reload"),
        )
        self.enable_btn = self._action_button(
            "Enable",
            lambda: self._perform_action("enable"),
        )
        self.disable_btn = self._action_button(
            "Disable",
            lambda: self._perform_action("disable"),
        )
        self.folder_btn = self._action_button(
            "Open Folder",
            self._open_selected_folder,
        )

        for index, button in enumerate(
            (
                self.start_btn,
                self.stop_btn,
                self.reload_btn,
                self.enable_btn,
                self.disable_btn,
                self.folder_btn,
            )
        ):
            action_grid.addWidget(button, index // 3, index % 3)

        detail_layout.addLayout(action_grid)
        splitter.addWidget(detail_panel)
        splitter.setSizes([680, 420])

        layout.addWidget(splitter, 1)
        return page

    def _build_hotpatch_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        heading = QLabel("HOT PATCH WORKSPACE")
        heading.setStyleSheet(
            "color:#23B8FF;font-size:17px;font-weight:800;"
            "background:transparent;"
        )
        layout.addWidget(heading)

        info = QLabel(
            "This remains separate from Integration Hub. It is intended for "
            "fast local component replacement with syntax validation, backup "
            "and live module reload."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "color:#9EB6CF;font-size:11px;background:transparent;"
        )
        layout.addWidget(info)

        self.drop_zone = SmartDropZone(self.project_root)
        self.drop_zone.file_dropped.connect(self._on_patch_selected)
        layout.addWidget(self.drop_zone)

        override_group = QGroupBox("Target override")
        override_layout = QHBoxLayout(override_group)

        for label, directory in (
            ("Plugins", "buster/plugins/"),
            ("Brain", "buster/brain/"),
            ("Automation", "buster/automation/"),
            ("Kernel", "buster/kernel/"),
            ("UI Panels", "buster/ui/v9/panels/"),
            ("Runtime", "buster/runtime/"),
            ("Core", "buster/core/"),
            ("Agents", "buster/agents/"),
        ):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, target=directory:
                    self._set_target_override(target, checked)
            )
            self._override_buttons[directory] = button
            override_layout.addWidget(button)

        self.clear_override_btn = QPushButton("Auto Route")
        self.clear_override_btn.setToolTip(
            "Clear the manual category override and use AST routing."
        )
        self.clear_override_btn.clicked.connect(
            self._clear_target_override
        )
        override_layout.addWidget(self.clear_override_btn)

        override_layout.addStretch()
        layout.addWidget(override_group)

        self.override_status_label = QLabel(
            "Routing mode: AST suggestion"
        )
        self.override_status_label.setStyleSheet(
            "color:#8FA9C4;font-size:10px;font-weight:700;"
            "background:transparent;"
        )
        layout.addWidget(self.override_status_label)

        self.patch_status = QPlainTextEdit()
        self.patch_status.setReadOnly(True)
        self.patch_status.setMaximumHeight(150)
        self.patch_status.setPlainText("No patch selected.")
        layout.addWidget(self.patch_status)

        patch_actions = QHBoxLayout()
        patch_actions.addStretch()

        self.preview_patch_btn = QPushButton("Validate")
        self.preview_patch_btn.setEnabled(False)
        self.preview_patch_btn.clicked.connect(self._validate_patch)
        patch_actions.addWidget(self.preview_patch_btn)

        self.apply_patch_btn = QPushButton("Apply Hot Patch")
        self.apply_patch_btn.setEnabled(False)
        self.apply_patch_btn.clicked.connect(self._apply_hot_patch)
        patch_actions.addWidget(self.apply_patch_btn)

        layout.addLayout(patch_actions)
        layout.addStretch()
        return page

    def _build_commands_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        row = QHBoxLayout()
        row.addWidget(QLabel("Available plugin commands"))
        row.addStretch()

        self.copy_command_btn = QPushButton("Copy Selected")
        self.copy_command_btn.clicked.connect(self._copy_selected_command)
        row.addWidget(self.copy_command_btn)

        self.execute_command_btn = QPushButton("Execute")
        self.execute_command_btn.clicked.connect(
            self._execute_selected_command
        )
        row.addWidget(self.execute_command_btn)

        layout.addLayout(row)

        self.command_list = QListWidget()
        self.command_list.itemDoubleClicked.connect(
            lambda _: self._execute_selected_command()
        )
        layout.addWidget(self.command_list, 1)

        self.command_help = QPlainTextEdit()
        self.command_help.setReadOnly(True)
        self.command_help.setMaximumHeight(130)
        self.command_help.setPlaceholderText(
            "Select a command to see its owning plugin."
        )
        self.command_list.currentItemChanged.connect(
            self._show_command_help
        )
        layout.addWidget(self.command_help)
        return page

    def _build_events_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        row = QHBoxLayout()
        row.addWidget(QLabel("Plugin lifecycle event stream"))
        row.addStretch()

        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear_events)
        row.addWidget(clear)
        layout.addLayout(row)

        self.event_log = QPlainTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.document().setMaximumBlockCount(1000)
        layout.addWidget(self.event_log, 1)

        self._append_event("Plugin Manager ready.")
        return page

    def _action_button(
        self,
        text: str,
        callback: Callable[[], None],
    ) -> QPushButton:
        button = QPushButton(text)
        button.setEnabled(False)
        button.clicked.connect(callback)
        return button

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def refresh_plugins(self) -> None:
        selected = self._selected_key
        records: dict[str, PluginRecord] = {}

        for record in self._discover_runtime_plugins():
            records[record.key] = record

        for record in self._discover_filesystem_plugins():
            existing = records.get(record.key)
            if existing is None:
                records[record.key] = record
            elif existing.path is None:
                existing.path = record.path
                if not existing.module_name:
                    existing.module_name = record.module_name

        self._records = records
        self._runtime_commands = self._discover_runtime_commands()
        self._merge_runtime_commands_into_records()
        self._render_plugin_table()
        self._render_commands()

        runtime_ready = self.runtime_core is not None
        self.runtime_status.setText(
            "● Runtime connected"
            if runtime_ready
            else "● Runtime unavailable"
        )
        self.runtime_status.setStyleSheet(
            (
                "color:#31D158;font-weight:700;background:transparent;"
                if runtime_ready
                else "color:#FFB000;font-weight:700;background:transparent;"
            )
        )

        if selected and selected in self._records:
            self._select_record(selected)

        self._append_event(
            f"Discovery refreshed: {len(self._records)} plugin(s)."
        )

    def _discover_runtime_plugins(self) -> Iterable[PluginRecord]:
        if self.runtime_core is None:
            return []

        sources: list[Any] = []
        for name in (
            "plugin_manager",
            "plugins",
            "plugin_registry",
            "registry",
        ):
            value = getattr(self.runtime_core, name, None)
            if value is not None:
                sources.append(value)

        services = getattr(self.runtime_core, "services", None)
        if services is not None:
            for name in ("plugin_manager", "plugins", "plugin_registry"):
                value = self._lookup_service(services, name)
                if value is not None:
                    sources.append(value)

        records: list[PluginRecord] = []
        seen_sources: set[int] = set()

        for source in sources:
            if id(source) in seen_sources:
                continue
            seen_sources.add(id(source))

            for key, plugin in self._iter_plugin_objects(source):
                records.append(
                    self._normalize_plugin(key, plugin, source="runtime")
                )

        return records

    def _lookup_service(self, services: Any, name: str) -> Any:
        if isinstance(services, dict):
            return services.get(name)

        for method_name in ("get", "resolve", "service"):
            method = getattr(services, method_name, None)
            if callable(method):
                try:
                    value = method(name)
                    if value is not None:
                        return value
                except Exception:
                    continue

        return getattr(services, name, None)

    def _iter_plugin_objects(
        self,
        source: Any,
    ) -> Iterable[tuple[str, Any]]:
        if isinstance(source, dict):
            yield from source.items()
            return

        for method_name in (
            "list_plugins",
            "plugins",
            "all",
            "items",
            "registered_plugins",
        ):
            member = getattr(source, method_name, None)

            try:
                value = member() if callable(member) else member
            except Exception:
                continue

            if isinstance(value, dict):
                yield from value.items()
                return

            if isinstance(value, (list, tuple, set)):
                for index, plugin in enumerate(value):
                    key = self._value(
                        plugin,
                        "key",
                        "id",
                        "name",
                        default=f"plugin_{index}",
                    )
                    yield str(key), plugin
                return

    def _normalize_plugin(
        self,
        key: str,
        plugin: Any,
        source: str,
    ) -> PluginRecord:
        name = str(
            self._value(plugin, "display_name", "name", default=key)
        )
        status = str(
            self._value(
                plugin,
                "status",
                "state",
                default=(
                    "Running"
                    if self._value(plugin, "running", default=False)
                    else "Stopped"
                ),
            )
        )
        version = str(
            self._value(plugin, "version", "__version__", default="—")
        )
        description = str(
            self._value(plugin, "description", "summary", default="")
        )
        author = str(self._value(plugin, "author", default="—"))
        module_name = str(
            self._value(
                plugin,
                "module_name",
                "module",
                default=getattr(plugin, "__module__", ""),
            )
        )
        commands = self._as_string_list(
            self._value(plugin, "commands", default=[])
        )
        dependencies = self._as_string_list(
            self._value(plugin, "dependencies", "requires", default=[])
        )
        permissions = self._as_string_list(
            self._value(plugin, "permissions", "capabilities", default=[])
        )
        health = str(
            self._value(
                plugin,
                "health",
                "health_status",
                default="Unknown",
            )
        )
        enabled = bool(self._value(plugin, "enabled", default=True))

        path_value = self._value(plugin, "path", "file_path", default=None)
        path = Path(path_value).resolve() if path_value else None

        return PluginRecord(
            key=str(key),
            name=name,
            status=status,
            version=version,
            description=description,
            author=author,
            module_name=module_name,
            path=path,
            commands=commands,
            dependencies=dependencies,
            permissions=permissions,
            health=health,
            enabled=enabled,
            source=source,
            raw=plugin,
        )

    def _discover_filesystem_plugins(self) -> Iterable[PluginRecord]:
        candidates = (
            self.project_root / "buster" / "plugins",
            self.project_root / "plugins",
        )

        records: list[PluginRecord] = []

        for directory in candidates:
            if not directory.exists():
                continue

            for path in sorted(directory.rglob("*.py")):
                if path.name == "__init__.py" or "__pycache__" in path.parts:
                    continue

                try:
                    relative = path.relative_to(self.project_root)
                except ValueError:
                    continue

                module_name = ".".join(relative.with_suffix("").parts)
                key = path.stem
                metadata = self._inspect_plugin_source(path)

                records.append(
                    PluginRecord(
                        key=key,
                        name=str(
                            metadata.get("name")
                            or key.replace("_", " ").title()
                        ),
                        status=(
                            "Loaded"
                            if module_name in sys.modules
                            else "Available"
                        ),
                        version=str(metadata.get("version") or "—"),
                        description=str(metadata.get("description") or ""),
                        author=str(metadata.get("author") or "—"),
                        module_name=module_name,
                        path=path.resolve(),
                        commands=list(metadata.get("commands") or []),
                        dependencies=list(
                            metadata.get("dependencies") or []
                        ),
                        permissions=list(
                            metadata.get("permissions") or []
                        ),
                        health="Not checked",
                        source="filesystem",
                    )
                )

        return records

    def _inspect_plugin_source(self, path: Path) -> dict[str, Any]:
        """Extract plugin metadata and commands without importing the module."""
        result: dict[str, Any] = {
            "commands": [],
            "dependencies": [],
            "permissions": [],
        }

        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
        except Exception as exc:
            logger.debug("Could not inspect plugin source %s: %s", path, exc)
            return result

        commands: set[str] = set()

        def literal(node: ast.AST, default: Any = None) -> Any:
            try:
                return ast.literal_eval(node)
            except Exception:
                return default

        # Module-level metadata and command dictionaries/lists.
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    node.targets
                    if isinstance(node, ast.Assign)
                    else [node.target]
                )
                value_node = node.value
                if value_node is None:
                    continue

                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue

                    name = target.id.lower()
                    value = literal(value_node)

                    if name in {
                        "plugin_name",
                        "name",
                        "display_name",
                    } and isinstance(value, str):
                        result["name"] = value
                    elif name in {"version", "__version__"} and isinstance(
                        value, (str, int, float)
                    ):
                        result["version"] = str(value)
                    elif name in {"author", "__author__"} and isinstance(
                        value, str
                    ):
                        result["author"] = value
                    elif name in {"description", "summary"} and isinstance(
                        value, str
                    ):
                        result["description"] = value
                    elif name in {
                        "dependencies",
                        "requires",
                    } and isinstance(value, (list, tuple, set)):
                        result["dependencies"] = [
                            str(item) for item in value
                        ]
                    elif name in {
                        "permissions",
                        "capabilities",
                    } and isinstance(value, (list, tuple, set)):
                        result["permissions"] = [
                            str(item) for item in value
                        ]
                    elif name in {
                        "commands",
                        "command_map",
                        "command_registry",
                        "handlers",
                    }:
                        if isinstance(value, dict):
                            commands.update(str(item) for item in value)
                        elif isinstance(value, (list, tuple, set)):
                            commands.update(str(item) for item in value)

        # Function decorators, register calls and commands() return values.
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        decorator_name = self._ast_call_name(decorator.func)
                        if decorator_name.endswith(
                            (
                                "command",
                                "register_command",
                                "command_handler",
                            )
                        ) and decorator.args:
                            value = literal(decorator.args[0])
                            if isinstance(value, str):
                                commands.add(value)

                if node.name in {
                    "commands",
                    "get_commands",
                    "list_commands",
                }:
                    for child in ast.walk(node):
                        if not isinstance(child, ast.Return):
                            continue
                        returned = literal(child.value) if child.value else None
                        if isinstance(returned, dict):
                            commands.update(str(item) for item in returned)
                        elif isinstance(returned, (list, tuple, set)):
                            commands.update(str(item) for item in returned)

            if isinstance(node, ast.Call):
                call_name = self._ast_call_name(node.func)
                if call_name.endswith(
                    (
                        "register_command",
                        "add_command",
                        "register_handler",
                        "register",
                    )
                ) and node.args:
                    value = literal(node.args[0])
                    if isinstance(value, str) and self._looks_like_command(
                        value
                    ):
                        commands.add(value)

        result["commands"] = sorted(commands)
        return result

    @staticmethod
    def _ast_call_name(node: ast.AST) -> str:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    @staticmethod
    def _looks_like_command(value: str) -> bool:
        value = value.strip()
        if not value or " " in value or len(value) > 120:
            return False
        return "." in value or value.replace("_", "").isalnum()

    def _discover_runtime_commands(self) -> dict[str, Any]:
        """Collect commands from Buster's central routers and registries."""
        discovered: dict[str, Any] = {}
        seen: set[int] = set()

        candidates: list[Any] = []

        if self.runtime_core is not None:
            for name in (
                "command_router",
                "command_registry",
                "commands",
                "router",
                "dispatcher",
                "registry",
            ):
                value = getattr(self.runtime_core, name, None)
                if value is not None:
                    candidates.append(value)

            services = getattr(self.runtime_core, "services", None)
            if services is not None:
                for name in (
                    "command_router",
                    "command_registry",
                    "commands",
                ):
                    value = self._lookup_service(services, name)
                    if value is not None:
                        candidates.append(value)

            kernel = getattr(self.runtime_core, "kernel", None)
            if kernel is not None:
                for name in (
                    "command_router",
                    "command_registry",
                    "commands",
                    "router",
                ):
                    value = getattr(kernel, name, None)
                    if value is not None:
                        candidates.append(value)

        if self.live is not None:
            for name in (
                "command_router",
                "command_registry",
                "commands",
            ):
                value = getattr(self.live, name, None)
                if value is not None:
                    candidates.append(value)

        for candidate in candidates:
            if id(candidate) in seen:
                continue
            seen.add(id(candidate))
            self._extract_commands_from_container(
                candidate,
                discovered,
            )

        return discovered

    def _extract_commands_from_container(
        self,
        container: Any,
        output: dict[str, Any],
    ) -> None:
        if container is None:
            return

        if isinstance(container, dict):
            for name, handler in container.items():
                if self._looks_like_command(str(name)):
                    output.setdefault(str(name), handler)
            return

        # Known internal storage attribute names.
        for attr_name in (
            "_commands",
            "commands",
            "_handlers",
            "handlers",
            "_registry",
            "registry",
            "_routes",
            "routes",
            "command_map",
        ):
            try:
                value = getattr(container, attr_name, None)
            except Exception:
                continue

            if callable(value):
                try:
                    value = value()
                except TypeError:
                    continue
                except Exception:
                    continue

            if isinstance(value, dict):
                for name, handler in value.items():
                    if self._looks_like_command(str(name)):
                        output.setdefault(str(name), handler)
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    name = self._command_name_from_item(item)
                    if name:
                        output.setdefault(name, item)

        # Known listing methods.
        for method_name in (
            "list_commands",
            "get_commands",
            "all_commands",
            "available_commands",
            "items",
            "all",
        ):
            method = getattr(container, method_name, None)
            if not callable(method):
                continue

            try:
                value = method()
            except Exception:
                continue

            if isinstance(value, dict):
                for name, handler in value.items():
                    if self._looks_like_command(str(name)):
                        output.setdefault(str(name), handler)
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    name = self._command_name_from_item(item)
                    if name:
                        output.setdefault(name, item)

    def _command_name_from_item(self, item: Any) -> Optional[str]:
        if isinstance(item, str):
            return item if self._looks_like_command(item) else None

        if isinstance(item, dict):
            for key in ("name", "command", "id", "key"):
                value = item.get(key)
                if value and self._looks_like_command(str(value)):
                    return str(value)

        for attr in ("name", "command", "command_name", "key", "id"):
            value = getattr(item, attr, None)
            if value and self._looks_like_command(str(value)):
                return str(value)

        return None

    def _merge_runtime_commands_into_records(self) -> None:
        """Attach central commands to their likely owning plugin."""
        self._command_owners.clear()

        for command, handler in self._runtime_commands.items():
            owner_key = self._infer_command_owner(command, handler)
            self._command_owners[command] = owner_key

            record = self._records.get(owner_key)
            if record is None:
                record = PluginRecord(
                    key=owner_key,
                    name=owner_key.replace("_", " ").title(),
                    status="Runtime",
                    health="Unknown",
                    source="command-registry",
                )
                self._records[owner_key] = record

            if command not in record.commands:
                record.commands.append(command)
                record.commands.sort()

    def _infer_command_owner(self, command: str, handler: Any) -> str:
        prefix = command.split(".", 1)[0].strip().lower()

        for key, record in self._records.items():
            candidates = {
                key.lower(),
                record.name.lower().replace(" ", "_"),
                record.name.lower().replace(" ", ""),
                Path(record.module_name).name.lower()
                if record.module_name
                else "",
            }
            if prefix in candidates or any(
                candidate.startswith(prefix)
                for candidate in candidates
                if candidate
            ):
                return key

        module_name = getattr(handler, "__module__", "")
        if not module_name and hasattr(handler, "__class__"):
            module_name = getattr(handler.__class__, "__module__", "")

        if module_name:
            module_tail = module_name.rsplit(".", 1)[-1].lower()
            for key, record in self._records.items():
                if (
                    record.module_name == module_name
                    or key.lower() == module_tail
                    or record.module_name.endswith(f".{module_tail}")
                ):
                    return key

        return prefix or "runtime"

    @staticmethod
    def _value(
        obj: Any,
        *names: str,
        default: Any = None,
    ) -> Any:
        for name in names:
            if isinstance(obj, dict) and name in obj:
                value = obj[name]
            else:
                value = getattr(obj, name, None)

            if callable(value) and name in {
                "commands",
                "dependencies",
                "permissions",
                "capabilities",
            }:
                try:
                    value = value()
                except Exception:
                    continue

            if value is not None:
                return value

        return default

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            return [str(item) for item in value.keys()]
        if isinstance(value, str):
            return [value]
        try:
            return [str(item) for item in value]
        except TypeError:
            return [str(value)]

    # ------------------------------------------------------------------
    # Rendering and selection
    # ------------------------------------------------------------------

    def _render_plugin_table(self) -> None:
        query = self.search_box.text().strip().lower()
        records = sorted(
            self._records.values(),
            key=lambda record: record.name.lower(),
        )

        if query:
            records = [
                record
                for record in records
                if query
                in " ".join(
                    (
                        record.name,
                        record.key,
                        record.status,
                        record.module_name,
                        " ".join(record.commands),
                    )
                ).lower()
            ]

        self.plugin_table.setRowCount(len(records))

        for row, record in enumerate(records):
            values = (
                record.name,
                record.status,
                record.version,
                record.health,
                record.source,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, record.key)
                self.plugin_table.setItem(row, column, item)

        running = sum(
            1
            for record in self._records.values()
            if record.status.lower() in {"running", "loaded", "active"}
        )
        self.summary_label.setText(
            f"{len(self._records)} plugins · {running} active"
        )

    def _apply_filter(self) -> None:
        self._render_plugin_table()

    def _on_table_selection(self) -> None:
        row = self.plugin_table.currentRow()
        if row < 0:
            return

        item = self.plugin_table.item(row, 0)
        if item is None:
            return

        key = item.data(Qt.UserRole)
        if key:
            self._select_record(str(key))

    def _select_record(self, key: str) -> None:
        record = self._records.get(key)
        if record is None:
            return

        self._selected_key = key
        self.plugin_selected.emit(key)

        self.detail_title.setText(record.name)
        self.detail_text.setPlainText(
            "\n".join(
                (
                    f"Key: {record.key}",
                    f"Status: {record.status}",
                    f"Enabled: {record.enabled}",
                    f"Version: {record.version}",
                    f"Health: {record.health}",
                    f"Source: {record.source}",
                    f"Module: {record.module_name or '—'}",
                    f"Path: {record.path or '—'}",
                    f"Author: {record.author}",
                    "",
                    "Description",
                    record.description or "No description supplied.",
                    "",
                    "Commands",
                    "\n".join(
                        f"  • {command}"
                        for command in record.commands
                    )
                    or "  None exposed",
                    "",
                    "Dependencies",
                    "\n".join(
                        f"  • {dependency}"
                        for dependency in record.dependencies
                    )
                    or "  None declared",
                    "",
                    "Permissions",
                    "\n".join(
                        f"  • {permission}"
                        for permission in record.permissions
                    )
                    or "  None declared",
                )
            )
        )

        for button in (
            self.start_btn,
            self.stop_btn,
            self.reload_btn,
            self.enable_btn,
            self.disable_btn,
        ):
            button.setEnabled(True)

        self.folder_btn.setEnabled(record.path is not None)

    def _render_commands(self) -> None:
        self.command_list.clear()
        command_count = 0

        for record in sorted(
            self._records.values(),
            key=lambda item: item.name.lower(),
        ):
            for command in sorted(set(record.commands)):
                item = QListWidgetItem(
                    f"{command}    [{record.name}]"
                )
                item.setData(Qt.UserRole, (record.key, command))
                self.command_list.addItem(item)
                command_count += 1

        if command_count == 0:
            item = QListWidgetItem(
                "No commands discovered — runtime registry is empty "
                "or not exposed."
            )
            item.setFlags(Qt.NoItemFlags)
            self.command_list.addItem(item)
            self.command_help.setPlainText(
                "The panel checked plugin objects, plugin source files, "
                "runtime command routers, service registries and kernel "
                "command registries, but no commands were available."
            )
        else:
            self.command_help.setPlaceholderText(
                f"{command_count} command(s) discovered. "
                "Select one to see its owning plugin."
            )

    # ------------------------------------------------------------------
    # Plugin actions
    # ------------------------------------------------------------------

    def _perform_action(self, action: str) -> None:
        record = self._records.get(self._selected_key or "")
        if record is None:
            return

        try:
            result = self._invoke_plugin_action(record, action)
            message = (
                str(result)
                if result not in (None, True)
                else f"{action.title()} completed."
            )
            self._append_event(
                f"{record.name}: {action} — {message}"
            )
            self.plugin_action_completed.emit(record.key, action)
            self.refresh_plugins()
        except Exception as exc:
            logger.exception(
                "Plugin action failed: %s %s",
                action,
                record.key,
            )
            QMessageBox.critical(
                self,
                "Plugin Action Failed",
                f"{record.name}\n\n{action}: {exc}",
            )
            self._append_event(
                f"ERROR {record.name}: {action} — {exc}"
            )

    def _invoke_plugin_action(
        self,
        record: PluginRecord,
        action: str,
    ) -> Any:
        targets: list[Any] = []

        for name in (
            "plugin_manager",
            "plugins",
            "plugin_registry",
        ):
            target = getattr(self.runtime_core, name, None)
            if target is not None:
                targets.append(target)

        if record.raw is not None:
            targets.append(record.raw)

        method_names = {
            "start": ("start_plugin", "start", "enable_plugin"),
            "stop": ("stop_plugin", "stop"),
            "reload": ("reload_plugin", "reload", "refresh_plugin"),
            "enable": ("enable_plugin", "enable"),
            "disable": ("disable_plugin", "disable"),
        }[action]

        errors: list[str] = []

        for target in targets:
            for method_name in method_names:
                method = getattr(target, method_name, None)
                if not callable(method):
                    continue

                for args in ((record.key,), (record.name,), ()):
                    try:
                        return method(*args)
                    except TypeError as exc:
                        errors.append(
                            f"{type(target).__name__}.{method_name}"
                            f"{args}: {exc}"
                        )
                        continue

        if action == "reload" and record.module_name:
            return self._reload_module(record.module_name)

        raise RuntimeError(
            "No compatible runtime action was found."
            + (
                "\n" + "\n".join(errors[-4:])
                if errors
                else ""
            )
        )

    def _reload_module(self, module_name: str) -> str:
        if module_name in sys.modules:
            importlib.invalidate_caches()
            importlib.reload(sys.modules[module_name])
            return f"Reloaded {module_name}"

        importlib.import_module(module_name)
        return f"Imported {module_name}"

    def _open_selected_folder(self) -> None:
        record = self._records.get(self._selected_key or "")
        if record is None or record.path is None:
            return

        folder = record.path if record.path.is_dir() else record.path.parent

        try:
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Open Folder",
                f"Could not open:\n{folder}\n\n{exc}",
            )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _show_command_help(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:
        del previous

        if current is None:
            self.command_help.clear()
            return

        key, command = current.data(Qt.UserRole)
        record = self._records.get(str(key))
        if record is None:
            return

        self.command_help.setPlainText(
            f"Command: {command}\n"
            f"Plugin: {record.name}\n"
            f"Module: {record.module_name or '—'}\n\n"
            "Double-click or press Execute to route this command through "
            "the runtime command interface."
        )

    def _copy_selected_command(self) -> None:
        item = self.command_list.currentItem()
        if item is None:
            return

        _, command = item.data(Qt.UserRole)
        QApplication = __import__(
            "PySide6.QtWidgets",
            fromlist=["QApplication"],
        ).QApplication
        QApplication.clipboard().setText(str(command))
        self._append_event(f"Copied command: {command}")

    def _execute_selected_command(self) -> None:
        item = self.command_list.currentItem()
        if item is None:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        _, command = data

        handler = self._runtime_commands.get(str(command))
        if callable(handler):
            try:
                result = handler()
                self._append_event(
                    f"Command executed: {command} — {result}"
                )
                return
            except TypeError:
                # Commands requiring arguments should still be routed by name.
                pass
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Command Failed",
                    f"{command}\n\n{exc}",
                )
                return

        for owner_name in (
            "command_router",
            "command_registry",
            "commands",
            "router",
            "dispatcher",
            "registry",
        ):
            owner = getattr(self.runtime_core, owner_name, None)
            if owner is None:
                continue

            for method_name in (
                "execute",
                "run",
                "dispatch",
                "handle",
                "invoke",
            ):
                method = getattr(owner, method_name, None)
                if not callable(method):
                    continue
                try:
                    result = method(str(command))
                    self._append_event(
                        f"Command executed: {command} — {result}"
                    )
                    return
                except TypeError:
                    continue
                except Exception as exc:
                    QMessageBox.critical(
                        self,
                        "Command Failed",
                        f"{command}\n\n{exc}",
                    )
                    return

        QMessageBox.information(
            self,
            "Command",
            "No compatible runtime command executor is exposed.\n\n"
            f"Command: {command}",
        )

    # ------------------------------------------------------------------
    # Hot patch
    # ------------------------------------------------------------------

    def _on_patch_selected(
        self,
        file_path: str,
        target_rel_path: str,
    ) -> None:
        self._selected_patch_file = Path(file_path).resolve()
        self._suggested_target_rel_path = target_rel_path

        if self._override_target_dir:
            self._target_rel_path = (
                f"{self._override_target_dir}"
                f"{self._selected_patch_file.name}"
            )
            routing_line = (
                f"Manual override: {self._target_rel_path}\n"
                f"AST suggestion ignored: {target_rel_path}"
            )
        else:
            self._target_rel_path = target_rel_path
            routing_line = f"AST suggestion: {target_rel_path}"

        self.preview_patch_btn.setEnabled(True)
        self.apply_patch_btn.setEnabled(False)

        self.patch_status.setPlainText(
            f"Selected: {self._selected_patch_file.name}\n"
            f"{routing_line}\n\n"
            "Run validation before applying."
        )
        self._append_event(
            f"Hot patch selected: {self._selected_patch_file.name} "
            f"→ {self._target_rel_path}"
        )

    def _set_target_override(
        self,
        directory: str,
        checked: bool = True,
    ) -> None:
        """Make a category button replace the automatic AST suggestion."""
        if not checked and self._override_target_dir == directory:
            self._clear_target_override()
            return

        self._override_target_dir = directory

        for target, button in self._override_buttons.items():
            button.blockSignals(True)
            button.setChecked(target == directory)
            button.blockSignals(False)

        label = next(
            (
                button.text()
                for target, button in self._override_buttons.items()
                if target == directory
            ),
            directory,
        )
        self.override_status_label.setText(
            f"Routing mode: manual override → {label}"
        )
        self.override_status_label.setStyleSheet(
            "color:#23B8FF;font-size:10px;font-weight:800;"
            "background:transparent;"
        )

        if self._selected_patch_file is not None:
            self._target_rel_path = (
                f"{directory}{self._selected_patch_file.name}"
            )
            self.patch_status.setPlainText(
                f"Selected: {self._selected_patch_file.name}\n"
                f"Manual override: {self._target_rel_path}\n"
                f"AST suggestion ignored: "
                f"{self._suggested_target_rel_path or 'Unavailable'}\n\n"
                "Run validation again before applying."
            )
            self.preview_patch_btn.setEnabled(True)
            self.apply_patch_btn.setEnabled(False)
            self._append_event(
                f"Target manually overridden: {self._target_rel_path}"
            )
        else:
            self.patch_status.setPlainText(
                f"Manual override armed: {directory}\n\n"
                "The next dropped file will be routed here instead of "
                "using the AST suggestion."
            )

    def _clear_target_override(self) -> None:
        """Return hot-patch routing to the AST-generated suggestion."""
        self._override_target_dir = None

        for button in self._override_buttons.values():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)

        self.override_status_label.setText(
            "Routing mode: AST suggestion"
        )
        self.override_status_label.setStyleSheet(
            "color:#8FA9C4;font-size:10px;font-weight:700;"
            "background:transparent;"
        )

        if (
            self._selected_patch_file is not None
            and self._suggested_target_rel_path
        ):
            self._target_rel_path = self._suggested_target_rel_path
            self.patch_status.setPlainText(
                f"Selected: {self._selected_patch_file.name}\n"
                f"AST suggestion restored: {self._target_rel_path}\n\n"
                "Run validation again before applying."
            )
            self.preview_patch_btn.setEnabled(True)
            self.apply_patch_btn.setEnabled(False)
            self._append_event(
                f"Automatic routing restored: {self._target_rel_path}"
            )
        else:
            self.patch_status.setPlainText(
                "Automatic AST routing restored.\n\n"
                "Drop or select a file."
            )

    # Compatibility with older callers.
    def _override_target(self, directory: str) -> None:
        self._set_target_override(directory, True)

    def _validate_patch(self) -> None:
        if (
            self._selected_patch_file is None
            or not self._target_rel_path
        ):
            return

        try:
            content = self._selected_patch_file.read_text(
                encoding="utf-8"
            )
            ast.parse(content)

            with tempfile.TemporaryDirectory(
                prefix="buster_patch_validate_"
            ) as temp_dir:
                temp_file = Path(temp_dir) / self._selected_patch_file.name
                temp_file.write_text(content, encoding="utf-8")
                py_compile.compile(
                    str(temp_file),
                    doraise=True,
                )

            target = (self.project_root / self._target_rel_path).resolve()
            if self.project_root not in target.parents:
                raise ValueError(
                    "Target resolves outside the Buster project root."
                )

            action = "overwrite" if target.exists() else "create"
            self.patch_status.appendPlainText(
                "\nVALIDATION PASSED\n"
                f"Action: {action}\n"
                f"Target: {target}\n"
                "Syntax: valid\n"
                "Compile: valid\n"
                "Project boundary: valid"
            )
            self.apply_patch_btn.setEnabled(True)
            self._append_event(
                f"Hot patch validation passed: {self._target_rel_path}"
            )
        except Exception as exc:
            self.apply_patch_btn.setEnabled(False)
            self.patch_status.appendPlainText(
                f"\nVALIDATION FAILED\n{exc}"
            )
            self._append_event(f"Hot patch validation failed: {exc}")

    def _apply_hot_patch(self) -> None:
        if (
            self._selected_patch_file is None
            or not self._target_rel_path
        ):
            return

        source = self._selected_patch_file
        target = (self.project_root / self._target_rel_path).resolve()

        if self.project_root not in target.parents:
            QMessageBox.critical(
                self,
                "Hot Patch Blocked",
                "The target is outside the project root.",
            )
            return

        confirmation = QMessageBox.question(
            self,
            "Apply Hot Patch",
            f"Apply:\n{source.name}\n\nTo:\n{target}?",
        )
        if confirmation != QMessageBox.Yes:
            return

        backup: Optional[Path] = None

        try:
            content = source.read_text(encoding="utf-8")
            ast.parse(content)

            target.parent.mkdir(parents=True, exist_ok=True)

            if target.exists():
                backup_dir = (
                    self.project_root
                    / "data"
                    / "hotpatch_backups"
                )
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = backup_dir / f"{target.name}.{stamp}.bak"
                shutil.copy2(target, backup)

            temp_target = target.with_suffix(target.suffix + ".tmp")
            temp_target.write_text(content, encoding="utf-8")
            py_compile.compile(str(temp_target), doraise=True)
            os.replace(temp_target, target)

            module_name = ".".join(
                target.relative_to(self.project_root)
                .with_suffix("")
                .parts
            )
            importlib.invalidate_caches()

            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)

            self._publish_runtime_event(
                "plugin.hotpatch.applied",
                {
                    "source": str(source),
                    "target": str(target),
                    "module": module_name,
                    "backup": str(backup) if backup else None,
                },
            )

            self.patch_status.appendPlainText(
                "\nHOT PATCH APPLIED\n"
                f"Module: {module_name}\n"
                f"Backup: {backup or 'Not required'}"
            )
            self.apply_patch_btn.setEnabled(False)
            self._append_event(
                f"Hot patch applied: {module_name}"
            )
            self.refresh_plugins()

        except Exception as exc:
            logger.exception("Hot patch failed")

            try:
                if backup and backup.exists():
                    shutil.copy2(backup, target)
            except Exception:
                logger.exception("Hot patch rollback failed")

            QMessageBox.critical(
                self,
                "Hot Patch Failed",
                str(exc),
            )
            self.patch_status.appendPlainText(
                f"\nHOT PATCH FAILED\n{exc}\n"
                "Existing file restored when a backup was available."
            )
            self._append_event(f"Hot patch failed: {exc}")

    # ------------------------------------------------------------------
    # Runtime events
    # ------------------------------------------------------------------

    def _connect_runtime_events(self) -> None:
        if self.runtime_core is None:
            return

        candidates = [
            getattr(self.runtime_core, name, None)
            for name in (
                "event_bus",
                "event_router",
                "dispatcher",
                "router",
            )
        ]

        for candidate in candidates:
            if candidate is None:
                continue

            for method_name in ("subscribe", "on", "register"):
                method = getattr(candidate, method_name, None)
                if not callable(method):
                    continue

                for topic in (
                    "plugin.*",
                    "plugin.loaded",
                    "plugin.started",
                    "plugin.stopped",
                    "plugin.reloaded",
                    "plugin.error",
                    "plugin.hotpatch.applied",
                ):
                    try:
                        result = method(topic, self._on_runtime_event)
                        if callable(result):
                            self._event_unsubscribers.append(result)
                    except Exception:
                        continue

                return

    def _on_runtime_event(self, event: Any) -> None:
        if isinstance(event, dict):
            event_type = (
                event.get("type")
                or event.get("event_type")
                or event.get("topic")
                or "plugin.event"
            )
            detail = (
                event.get("message")
                or event.get("detail")
                or event.get("payload")
                or event
            )
        else:
            event_type = getattr(
                event,
                "event_type",
                getattr(event, "type", "plugin.event"),
            )
            detail = getattr(
                event,
                "payload",
                getattr(event, "message", event),
            )

        self._append_event(f"{event_type}: {detail}")

    def _publish_runtime_event(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        if self.runtime_core is None:
            return

        for owner_name in (
            "event_bus",
            "event_router",
            "dispatcher",
            "router",
        ):
            owner = getattr(self.runtime_core, owner_name, None)
            if owner is None:
                continue

            for method_name in ("publish", "emit", "dispatch"):
                method = getattr(owner, method_name, None)
                if not callable(method):
                    continue

                for args in (
                    (event_type, payload),
                    ({"type": event_type, "payload": payload},),
                ):
                    try:
                        method(*args)
                        return
                    except TypeError:
                        continue
                    except Exception:
                        logger.exception(
                            "Could not publish plugin event"
                        )
                        return

    def _append_event(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.event_log.appendPlainText(f"{timestamp}  {message}")

    def _clear_events(self) -> None:
        self.event_log.clear()
        self._append_event("Event stream cleared.")

    def closeEvent(self, event) -> None:
        for unsubscribe in self._event_unsubscribers:
            try:
                unsubscribe()
            except Exception:
                pass
        self._event_unsubscribers.clear()
        super().closeEvent(event)


def create_brain_button(parent=None) -> QPushButton:
    """Compatibility factory for existing Mission Control integrations."""

    button = QPushButton("🧠 Plugins & Hot Patch", parent)
    button.setFixedHeight(36)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(
        """
        QPushButton {
            background:#10253A;
            color:#23B8FF;
            border:1px solid #2878B8;
            border-radius:8px;
            font-size:13px;
            font-weight:700;
            padding:0 16px;
            text-align:left;
        }
        QPushButton:hover {
            background:#1C4163;
            border-color:#23B8FF;
            color:#FFFFFF;
        }
        QPushButton:pressed {
            background:#20527A;
        }
        """
    )
    return button
