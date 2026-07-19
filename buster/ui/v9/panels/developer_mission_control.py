from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,  # Added to prevent vertical clipping
)

from buster.ui.v9.panels.runtime_panel.runtime_workspace import RuntimeWorkspace


class RuntimeSummaryPanel(QFrame):
    """Compact live runtime intelligence sidebar."""

    def __init__(self, runtime_core=None, parent=None):
        super().__init__(parent)
        self.runtime_core = runtime_core
        self._subscribed = False
        self._event_count = 0
        self._error_count = 0
        self._active_agents: set[str] = set()
        self._running_jobs: set[str] = set()
        self._queued_jobs = 0

        self.setObjectName("RuntimeSummaryPanel")
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)
        self.setStyleSheet(
            """
            QFrame#RuntimeSummaryPanel {
                background: #07111D;
                border-left: 1px solid #15324E;
            }

            QLabel {
                border: none;
                background: transparent;
            }

            QPushButton {
                background: #0A1D33;
                color: #DCEBFF;
                border: 1px solid #175A94;
                border-radius: 7px;
                padding: 7px 10px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #0E2A49;
                border-color: #23B8FF;
            }
            """
        )

        self._build_ui()
        self._connect_runtime()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10) # Margins tightened slightly to save vertical space

        title = QLabel("RUNTIME INTELLIGENCE")
        title.setStyleSheet(
            "color:#23B8FF;font-size:14px;font-weight:800;letter-spacing:1px;"
        )
        root.addWidget(title)

        self.dispatcher_label = self._metric("Dispatcher", "Unknown")
        self.events_label = self._metric("Events", "0")
        self.agents_label = self._metric("Active Agents", "0")
        self.jobs_label = self._metric("Running Jobs", "0")
        self.queue_label = self._metric("Queue", "0")
        self.errors_label = self._metric("Errors", "0")

        section = QLabel("AGENT FLOW")
        section.setStyleSheet(
            "color:#7894B5;font-size:10px;font-weight:700;margin-top:4px;"
        )
        root.addWidget(section)

        self.flow_label = QLabel(
            "Planner\n   ↓\nBuilder\n   ↓\nTester\n   ↓\nReviewer"
        )
        self.flow_label.setAlignment(Qt.AlignCenter)
        self.flow_label.setStyleSheet(
            """
            color:#AFC8E6;
            background:#050B14;
            border:1px solid #14324F;
            border-radius:9px;
            padding:8px;
            font-family:Consolas;
            font-size:11px;
            """
        )
        root.addWidget(self.flow_label)

        section = QLabel("LATEST ACTIVITY")
        section.setStyleSheet(
            "color:#7894B5;font-size:10px;font-weight:700;margin-top:4px;"
        )
        root.addWidget(section)

        self.activity = QTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setMinimumHeight(100) # Ensure it keeps a useful height
        self.activity.setMaximumHeight(200)
        self.activity.setStyleSheet(
            """
            QTextEdit {
                background:#050B14;
                color:#BFD1E7;
                border:1px solid #14324F;
                border-radius:8px;
                padding:6px;
                font-family:Consolas;
                font-size:10px;
            }
            """
        )
        root.addWidget(self.activity)

        root.addStretch()

        refresh = QPushButton("Refresh Runtime")
        refresh.setFixedHeight(26)
        refresh.clicked.connect(self.refresh)
        root.addWidget(refresh)

    def _metric(self, name: str, value: str) -> QLabel:
        label = QLabel(f"{name}\n{value}")
        label.setStyleSheet(
            """
            color:#DCEBFF;
            background:#081827;
            border:1px solid #14324F;
            border-radius:8px;
            padding:6px;
            font-size:10px;
            """
        )
        self.layout().addWidget(label)
        return label

    def _connect_runtime(self) -> None:
        if self._subscribed or self.runtime_core is None:
            return

        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        if dispatcher is None:
            return

        dispatcher.subscribe("*", self._handle_event)
        self._subscribed = True

    def _handle_event(self, event: dict) -> None:
        if not isinstance(event, dict):
            return

        self._event_count += 1
        event_type = str(event.get("type", "unknown"))
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}

        if event_type.endswith(".failed") or event_type in {
            "error",
            "runtime.error",
        }:
            self._error_count += 1

        if event_type == "agent.started":
            agent = str(payload.get("agent", "Agent"))
            self._active_agents.add(agent)
        elif event_type in {"agent.finished", "agent.failed"}:
            agent = str(payload.get("agent", "Agent"))
            self._active_agents.discard(agent)

        if event_type in {"job.created", "job.queued"}:
            self._queued_jobs += 1
        elif event_type == "job.started":
            job = str(
                payload.get("job_id")
                or payload.get("job")
                or payload.get("title")
                or "job"
            )
            self._running_jobs.add(job)
            self._queued_jobs = max(0, self._queued_jobs - 1)
        elif event_type in {"job.finished", "job.failed"}:
            job = str(
                payload.get("job_id")
                or payload.get("job")
                or payload.get("title")
                or "job"
            )
            self._running_jobs.discard(job)

        summary = self._event_summary(event_type, payload)
        self.activity.append(f"{event_type}\n{summary}\n")
        scrollbar = self.activity.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _event_summary(self, event_type: str, payload: dict) -> str:
        for key in (
            "message",
            "summary",
            "request",
            "title",
            "agent",
            "job_id",
            "status",
            "error",
        ):
            value = payload.get(key)
            if value not in (None, "", [], {}):
                return str(value)[:180]

        return str(payload)[:180] if payload else "Event received"

    def refresh(self) -> None:
        dispatcher_status = "Unavailable"
        subscribers = 0

        if self.runtime_core is not None:
            dispatcher = getattr(self.runtime_core, "dispatcher", None)
            if dispatcher is not None:
                try:
                    status = dispatcher.status()
                    dispatcher_status = "Healthy"
                    subscribers = sum(
                        status.get("subscribers", {}).values()
                    )
                except Exception:
                    dispatcher_status = "Degraded"

        self.dispatcher_label.setText(
            f"Dispatcher\n{dispatcher_status} · {subscribers} subscribers"
        )
        self.events_label.setText(f"Events\n{self._event_count}")
        self.agents_label.setText(
            f"Active Agents\n{len(self._active_agents)}"
        )
        self.jobs_label.setText(
            f"Running Jobs\n{len(self._running_jobs)}"
        )
        self.queue_label.setText(f"Queue\n{self._queued_jobs}")
        self.errors_label.setText(f"Errors\n{self._error_count}")

        stages = []
        for name in ("Planner", "Builder", "Tester", "Reviewer"):
            active = any(name.lower() in agent.lower() for agent in self._active_agents)
            stages.append(f"{'●' if active else '○'} {name}")

        self.flow_label.setText("\n   ↓\n".join(stages))

    def shutdown(self) -> None:
        if self.timer.isActive():
            self.timer.stop()

        if not self._subscribed or self.runtime_core is None:
            return

        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        if dispatcher is not None:
            try:
                dispatcher.unsubscribe("*", self._handle_event)
            except Exception:
                pass

        self._subscribed = False


class DeveloperMissionControl(QWidget):
    """
    Unified Buster developer environment.
    """

    def __init__(
        self,
        runtime_core=None,
        live=None,
        parent=None,
    ):
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.live = live
        self._pages: dict[str, QWidget] = {}

        self.setWindowTitle("Buster Developer Mission Control")
        # Reduced initial size to comfortable fit on standard laptop screens
        self.resize(1100, 700) 
        self.setObjectName("DeveloperMissionControl")
        self.setStyleSheet(
            """
            QWidget#DeveloperMissionControl {
                background:#050B14;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }

            QListWidget {
                background:#07111D;
                color:#BFD1E7;
                border:none;
                border-right:1px solid #15324E;
                outline:none;
                padding:8px;
                font-size:13px;
                font-weight:600;
            }

            QListWidget::item {
                padding:10px 9px;
                border-radius:7px;
                margin:2px 0;
            }

            QListWidget::item:selected {
                background:#0E2A49;
                color:#23B8FF;
            }

            QSplitter::handle {
                background:#10253A;
            }
            """
        )

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(18, 14, 18, 12)

        title_box = QVBoxLayout()

        title = QLabel("BUSTER DEVELOPER MISSION CONTROL")
        title.setStyleSheet(
            "color:#23B8FF;font-size:20px;font-weight:800;letter-spacing:1px;"
        )

        subtitle = QLabel(
            "Projects · Runtime · Agents · Plugins · Terminal · Intelligence"
        )
        subtitle.setStyleSheet("color:#7894B5;font-size:11px;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.status_label = QLabel("● Runtime connected")
        self.status_label.setStyleSheet(
            "color:#31D158;font-size:12px;font-weight:700;"
        )
        header.addWidget(self.status_label)

        root.addLayout(header)

        outer_splitter = QSplitter(Qt.Horizontal)
        root.addWidget(outer_splitter, 1)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(150)
        outer_splitter.addWidget(self.navigation)

        centre_splitter = QSplitter(Qt.Vertical)
        outer_splitter.addWidget(centre_splitter)

        self.stack = QStackedWidget()
        # CRUCIAL: Protect the stacked view page from being completely crushed 
        self.stack.setMinimumHeight(350) 
        centre_splitter.addWidget(self.stack)

        self.bottom_dock = self._create_tool_page(
            "Runtime Terminal",
            "buster.ui.v9.panels.terminal_panel",
            "TerminalPanel",
            fallback_text="Runtime terminal is unavailable.",
        )
        # CRUCIAL: Prevent terminal from squishing layout below 90px
        self.bottom_dock.setMinimumHeight(90)
        centre_splitter.addWidget(self.bottom_dock)
        centre_splitter.setSizes([450, 150]) # Adjusted default weights

        self.runtime_summary = RuntimeSummaryPanel(
            runtime_core=self.runtime_core
        )

        # CRUCIAL: Wrap sidebar in a scroll area so it adapts beautifully when height is constrained
        scroll_sidebar = QScrollArea()
        scroll_sidebar.setWidgetResizable(True)
        scroll_sidebar.setWidget(self.runtime_summary)
        scroll_sidebar.setFrameShape(QFrame.NoFrame)
        scroll_sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_sidebar.setFixedWidth(210) # Lock width smoothly

        outer_splitter.addWidget(scroll_sidebar)
        outer_splitter.setSizes([150, 740, 210])

        page_specs = [
            ("Runtime", self._create_runtime_page),
            (
                "Projects",
                lambda: self._create_tool_page(
                    "Projects",
                    "buster.ui.v9.panels.project_panel",
                    "ProjectPanel",
                ),
            ),
            (
                "Agents",
                lambda: self._create_tool_page(
                    "Agent OS",
                    "buster.ui.v9.panels.agent_panel",
                    "AgentPanel",
                ),
            ),
            (
                "Plugins",
                lambda: self._create_tool_page(
                    "Plugin Manager",
                    "buster.ui.v9.panels.plugin_panel",
                    "PluginPanel",
                ),
            ),
            (
                "Workspace",
                lambda: self._create_tool_page(
                    "Workspace",
                    "buster.ui.v9.panels.workspace_panel",
                    "WorkspacePanel",
                ),
            ),
            (
                "Vision",
                lambda: self._create_tool_page(
                    "Vision",
                    "buster.ui.v9.panels.vision_panel",
                    "VisionPanel",
                ),
            ),
            (
                "Voice",
                lambda: self._create_tool_page(
                    "Voice",
                    "buster.ui.v9.panels.voice_panel",
                    "VoicePanel",
                ),
            ),
            (
                "Settings",
                lambda: self._create_tool_page(
                    "Settings",
                    "buster.ui.v9.panels.settings_panel",
                    "SettingsPanel",
                ),
            ),
        ]

        for name, factory in page_specs:
            page = factory()
            self._pages[name] = page
            self.stack.addWidget(page)
            self.navigation.addItem(QListWidgetItem(name))

        self.navigation.currentRowChanged.connect(
            self._change_page
        )
        self.navigation.setCurrentRow(0)

    def _create_runtime_page(self) -> QWidget:
        return RuntimeWorkspace(
            runtime_core=self.runtime_core,
            live=self.live,
        )

    def _create_tool_page(
        self,
        title: str,
        module_name: str,
        class_name: str,
        fallback_text: Optional[str] = None,
    ) -> QWidget:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)

            constructors: list[Callable[[], QWidget]] = [
                lambda: cls(self.live, self.runtime_core),
                lambda: cls(self.runtime_core, self.live),
                lambda: cls(self.live),
                lambda: cls(self.runtime_core),
                lambda: cls(),
            ]

            last_error: Optional[Exception] = None

            for constructor in constructors:
                try:
                    widget = constructor()
                    if isinstance(widget, QWidget):
                        return widget
                except TypeError as exc:
                    last_error = exc

            if last_error is not None:
                raise last_error

        except Exception as exc:
            return self._fallback_page(
                title,
                fallback_text or f"{title} could not be loaded.\n\n{exc}",
            )

        return self._fallback_page(
            title,
            fallback_text or f"{title} returned no widget.",
        )

    def _fallback_page(self, title: str, message: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)

        heading = QLabel(title.upper())
        heading.setStyleSheet(
            "color:#23B8FF;font-size:20px;font-weight:800;"
        )

        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet(
            "color:#9FB8D5;font-size:13px;"
        )

        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addStretch()
        return page

    def _change_page(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def closeEvent(self, event) -> None:
        self.runtime_summary.shutdown()
        event.accept()