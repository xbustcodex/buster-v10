from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from buster.runtime import create_runtime_core

try:
    from buster.runtime.repair_event_stream import RepairEventStream
except Exception:
    RepairEventStream = None


# ======================================================================
# Presenter state
# ======================================================================


@dataclass
class MissionControlState:
    payload: dict[str, Any] = field(default_factory=dict)
    runtime_status: dict[str, Any] = field(default_factory=dict)
    ai: dict[str, Any] = field(default_factory=dict)
    repair: dict[str, Any] = field(default_factory=dict)
    latest_event: dict[str, Any] = field(default_factory=dict)
    selected_section: str = "Dashboard"


# ======================================================================
# Runtime event bridge
# ======================================================================


class MissionControlEventBridge(QObject):
    """
    Bridges RuntimeDispatcher callbacks onto the Qt thread.

    Runtime callbacks may arrive from worker threads. The internal signal
    safely queues delivery to the presenter.
    """

    event_received = Signal(object)

    def __init__(
        self,
        runtime_core: Any,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.dispatcher = getattr(
            runtime_core,
            "dispatcher",
            None,
        )
        self._connected = False

        self._queued_event.connect(
            self._emit_event
        )
        self.connect_runtime()

    _queued_event = Signal(object)

    def connect_runtime(self) -> None:
        if self._connected:
            return

        subscribe = getattr(
            self.dispatcher,
            "subscribe",
            None,
        )

        if not callable(subscribe):
            return

        subscribe(
            "*",
            self._receive_runtime_event,
        )
        self._connected = True

    def disconnect_runtime(self) -> None:
        if not self._connected:
            return

        unsubscribe = getattr(
            self.dispatcher,
            "unsubscribe",
            None,
        )

        if callable(unsubscribe):
            try:
                unsubscribe(
                    "*",
                    self._receive_runtime_event,
                )
            except Exception:
                pass

        self._connected = False

    def _receive_runtime_event(
        self,
        event: Any,
    ) -> None:
        self._queued_event.emit(event)

    @Slot(object)
    def _emit_event(
        self,
        event: Any,
    ) -> None:
        self.event_received.emit(event)

    def close(self) -> None:
        self.disconnect_runtime()
        self.deleteLater()


# ======================================================================
# Presenter
# ======================================================================


class MissionControlPresenter(QObject):
    """
    Owns Mission Control state and runtime-event interpretation.

    The view renders state only. No polling timer is used.
    """

    state_changed = Signal(object)
    section_changed = Signal(str, object)
    ai_changed = Signal(object)
    repair_changed = Signal(object)
    event_received = Signal(object)
    error = Signal(str)

    RELEVANT_PREFIXES = (
        "runtime.",
        "job.",
        "agent.",
        "service.",
        "plugin.",
        "workflow.",
        "memory.",
        "blackboard.",
        "notification",
        "repair.",
        "self_improvement.",
        "autonomy.",
        "execution.",
    )

    def __init__(
        self,
        runtime_core: Any,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.core = runtime_core
        self.state = MissionControlState()

        self.bridge = MissionControlEventBridge(
            runtime_core,
            parent=self,
        )
        self.bridge.event_received.connect(
            self._on_runtime_event
        )

        self.repair_stream = None

        if RepairEventStream is not None:
            try:
                self.repair_stream = RepairEventStream(
                    runtime_core=runtime_core,
                    parent=self,
                )
                self.repair_stream.state_changed.connect(
                    self._on_repair_state
                )
            except Exception:
                self.repair_stream = None

        self.refresh_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_section(
        self,
        section: str,
    ) -> None:
        self.state.selected_section = (
            section or "Dashboard"
        )
        self._emit_selected_section()

    def refresh_all(self) -> None:
        try:
            self.state.payload = self._dashboard_payload()
            self.state.runtime_status = self._runtime_status()
            self.state.ai = self._ai_info()
            self.state.repair = self._repair_status()

            self.state_changed.emit(
                self.snapshot()
            )
            self.ai_changed.emit(
                dict(self.state.ai)
            )
            self.repair_changed.emit(
                dict(self.state.repair)
            )
            self._emit_selected_section()

        except Exception as exc:
            self.error.emit(str(exc))

    def refresh_runtime(self) -> None:
        try:
            self.state.runtime_status = self._runtime_status()
            self.state.payload = self._dashboard_payload()
            self.state.ai = self._ai_info()
            self.state.repair = self._repair_status()

            self.state_changed.emit(
                self.snapshot()
            )
            self.ai_changed.emit(
                dict(self.state.ai)
            )
            self.repair_changed.emit(
                dict(self.state.repair)
            )
            self._emit_selected_section()

        except Exception as exc:
            self.error.emit(str(exc))

    def snapshot(self) -> dict[str, Any]:
        return {
            "payload": dict(self.state.payload),
            "runtime_status": dict(
                self.state.runtime_status
            ),
            "ai": dict(self.state.ai),
            "repair": dict(self.state.repair),
            "latest_event": dict(
                self.state.latest_event
            ),
            "selected_section": (
                self.state.selected_section
            ),
        }

    def section_data(
        self,
        section: Optional[str] = None,
    ) -> Any:
        section = (
            section
            or self.state.selected_section
            or "Dashboard"
        )

        payload = self.state.payload
        runtime_status = self.state.runtime_status
        ai = self.state.ai
        repair = self.state.repair

        views = {
            "Dashboard": {
                "ai_runtime": ai,
                "repair_workflow": repair,
                "summary": payload.get(
                    "runtime",
                    {},
                ),
                "jobs": payload.get(
                    "jobs",
                    {},
                ).get(
                    "counts",
                    {},
                ),
                "recent_events": payload.get(
                    "events",
                    [],
                )[-8:],
            },
            "Runtime": {
                "runtime": runtime_status,
                "ai_runtime": ai,
                "repair_workflow": repair,
            },
            "Services": payload.get(
                "services",
                {},
            ),
            "Agents": payload.get(
                "agents",
                {},
            ),
            "Jobs": payload.get(
                "jobs",
                {},
            ),
            "Events": payload.get(
                "events",
                [],
            ),
            "Blackboard": self._blackboard_snapshot(),
            "Memory": self._memory_status(),
            "Plugins": payload.get(
                "plugins",
                {},
            ),
            "Workflow": {
                "workflow_graph": payload.get(
                    "workflow_graph",
                    {},
                ),
                "event_graph": payload.get(
                    "event_graph",
                    {},
                ),
                "repair_workflow": repair,
            },
        }

        return views.get(section, {})

    def inspector_data(self) -> dict[str, Any]:
        payload = self.state.payload
        runtime_status = self.state.runtime_status
        ai = self.state.ai
        repair = self.state.repair

        runtime_payload = payload.get(
            "runtime",
            {},
        )
        jobs_payload = payload.get(
            "jobs",
            {},
        )

        return {
            "selected": self.state.selected_section,
            "ai_provider": ai.get(
                "provider_label",
                "Unknown",
            ),
            "ai_model": ai.get(
                "model",
                "Unknown",
            ),
            "ai_connected": ai.get(
                "connected",
            ),
            "runtime_started": runtime_status.get(
                "started",
            ),
            "repair_state": repair.get(
                "state",
                repair.get(
                    "latest_session",
                    {},
                ).get(
                    "status",
                    "idle",
                )
                if isinstance(
                    repair.get("latest_session"),
                    Mapping,
                )
                else "idle",
            ),
            "active_repairs": repair.get(
                "active_sessions",
                repair.get(
                    "active_repairs",
                    0,
                ),
            ),
            "services": len(
                runtime_payload.get(
                    "services",
                    [],
                )
            ),
            "agents": len(
                runtime_payload.get(
                    "agents",
                    [],
                )
            ),
            "jobs": jobs_payload.get(
                "count",
                0,
            ),
            "events": runtime_payload.get(
                "event_count",
                0,
            ),
            "capabilities": self._capability_count(),
            "latest_event": dict(
                self.state.latest_event
            ),
        }

    def run_workflow(self) -> Any:
        if self.core is None:
            return None

        return self.core.run(
            "Review architecture quality and validate with tests"
        )

    def run_health(self) -> Any:
        if self.core is None:
            return None

        job = self.core.create_job(
            "Mission Control Health",
            "lifecycle.health",
            {
                "requested_by": (
                    "mission_control_v12"
                )
            },
        )
        return self.core.run_job(
            job["job_id"]
        )

    # ------------------------------------------------------------------
    # Runtime events
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_runtime_event(
        self,
        event: Any,
    ) -> None:
        data = self._event_to_dict(event)
        event_type = self._event_type(data)

        if not event_type:
            return

        self.state.latest_event = data
        self.event_received.emit(data)

        if not event_type.startswith(
            self.RELEVANT_PREFIXES
        ):
            return

        # Runtime state is maintained by RuntimeCore.refresh_state().
        # Read that shared state only when an actual runtime event arrives.
        self._refresh_for_event(event_type)

    def _refresh_for_event(
        self,
        event_type: str,
    ) -> None:
        try:
            if event_type.startswith("repair."):
                self.state.repair = (
                    self._repair_status()
                )
                self.repair_changed.emit(
                    dict(self.state.repair)
                )

            if event_type.startswith(
                (
                    "runtime.",
                    "service.",
                    "agent.",
                    "job.",
                    "plugin.",
                    "workflow.",
                    "memory.",
                    "blackboard.",
                    "repair.",
                    "self_improvement.",
                    "autonomy.",
                    "execution.",
                )
            ):
                self.state.runtime_status = (
                    self._runtime_status()
                )
                self.state.payload = (
                    self._dashboard_payload()
                )

            if event_type.startswith(
                (
                    "runtime.",
                    "service.",
                    "ai.",
                )
            ):
                self.state.ai = self._ai_info()
                self.ai_changed.emit(
                    dict(self.state.ai)
                )

            self.state_changed.emit(
                self.snapshot()
            )
            self._emit_selected_section()

        except Exception as exc:
            self.error.emit(str(exc))

    @Slot(object)
    def _on_repair_state(
        self,
        state: Any,
    ) -> None:
        if isinstance(state, Mapping):
            self.state.repair = dict(state)
            self.repair_changed.emit(
                dict(self.state.repair)
            )
            self.state_changed.emit(
                self.snapshot()
            )
            self._emit_selected_section()

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def _dashboard_payload(self) -> dict[str, Any]:
        if self.core is None:
            return {}

        try:
            value = (
                self.core
                .devtools
                .dashboard_payload()
            )
            return (
                dict(value)
                if isinstance(value, Mapping)
                else {}
            )
        except Exception as exc:
            return {
                "runtime": {
                    "error": str(exc),
                    "services": [],
                    "agents": [],
                    "event_count": 0,
                },
                "jobs": {
                    "count": 0,
                    "counts": {},
                },
                "events": [],
                "plugins": {},
                "services": {},
                "agents": {},
                "workflow_graph": {},
                "event_graph": {},
            }

    def _runtime_status(self) -> dict[str, Any]:
        if self.core is None:
            return {}

        try:
            value = self.core.status()
            return (
                dict(value)
                if isinstance(value, Mapping)
                else {}
            )
        except Exception as exc:
            return {
                "error": str(exc),
            }

    def _repair_status(self) -> dict[str, Any]:
        if self.core is None:
            return {}

        method = getattr(
            self.core,
            "repair_workflow_status",
            None,
        )

        if callable(method):
            try:
                value = method()
                return (
                    dict(value)
                    if isinstance(
                        value,
                        Mapping,
                    )
                    else {}
                )
            except Exception:
                pass

        status = self.state.runtime_status.get(
            "repair_workflow",
            {},
        )

        return (
            dict(status)
            if isinstance(status, Mapping)
            else {}
        )

    def _ai_info(self) -> dict[str, Any]:
        info = {
            "provider": "unknown",
            "provider_label": "Unknown",
            "model": "Unknown",
            "connected": False,
            "status": "Unavailable",
            "fallback": "Local Rules",
        }

        if self.core is None:
            return info

        manager = getattr(
            self.core,
            "ai_manager",
            None,
        )

        if manager is None:
            manager = getattr(
                self.core,
                "provider_manager",
                None,
            )

        if manager is None:
            return info

        labels = {
            "openrouter": "OpenRouter",
            "ollama": "Ollama",
            "lmstudio": "LM Studio",
            "local": "Local Rules",
        }

        try:
            key = str(
                getattr(
                    manager,
                    "current",
                    "unknown",
                )
            ).lower()

            provider = getattr(
                manager,
                "providers",
                {},
            ).get(key)

            model = getattr(
                provider,
                "model",
                "Unknown",
            )

            if provider is None:
                connected = False
                status = "Unavailable"
            elif key == "local":
                connected = True
                status = "Ready"
            else:
                connected = None
                status = "Configured"

            info.update({
                "provider": key,
                "provider_label": labels.get(
                    key,
                    key.replace(
                        "_",
                        " ",
                    ).title(),
                ),
                "model": str(
                    model or "Unknown"
                ),
                "connected": connected,
                "status": status,
            })

        except Exception as exc:
            info["status"] = (
                f"Error: {exc}"
            )

        return info

    def _blackboard_snapshot(self) -> Any:
        try:
            return self.core.blackboard.snapshot()
        except Exception:
            return {}

    def _memory_status(self) -> Any:
        try:
            return self.core.agent_memory.status()
        except Exception:
            return {}

    def _capability_count(self) -> int:
        try:
            capabilities = (
                self.core
                .registry
                .status()
                .get(
                    "capabilities",
                    {},
                )
            )
            return len(capabilities)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit_selected_section(self) -> None:
        section = (
            self.state.selected_section
            or "Dashboard"
        )
        self.section_changed.emit(
            section,
            self.section_data(section),
        )

    @staticmethod
    def _event_to_dict(
        event: Any,
    ) -> dict[str, Any]:
        if isinstance(event, Mapping):
            return dict(event)

        method = getattr(
            event,
            "to_dict",
            None,
        )

        if callable(method):
            try:
                value = method()
                if isinstance(value, Mapping):
                    return dict(value)
            except Exception:
                pass

        values = getattr(
            event,
            "__dict__",
            None,
        )

        return (
            dict(values)
            if isinstance(values, Mapping)
            else {}
        )

    @staticmethod
    def _event_type(
        event: Mapping[str, Any],
    ) -> str:
        return str(
            event.get("type")
            or event.get("event_type")
            or event.get("name")
            or ""
        )

    def close(self) -> None:
        if self.repair_stream is not None:
            try:
                self.repair_stream.close()
            except Exception:
                pass

        self.bridge.close()
        self.deleteLater()


# ======================================================================
# Mission Control view
# ======================================================================


class MissionControlV12(QWidget):
    PROVIDER_LABELS = {
        "openrouter": "OpenRouter",
        "ollama": "Ollama",
        "lmstudio": "LM Studio",
        "local": "Local Rules",
    }

    def __init__(
        self,
        runtime_core=None,
        parent=None,
    ):
        super().__init__(parent)

        self.core = (
            runtime_core
            or create_runtime_core(".")
        )
        self.setObjectName(
            "MissionControlV12"
        )

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self.presenter = (
            MissionControlPresenter(
                self.core,
                parent=self,
            )
        )
        self._connect_presenter()

        self.nav.setCurrentRow(0)
        self.presenter.set_section(
            "Dashboard"
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(
            16,
            16,
            16,
            16,
        )
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName(
            "HeaderCard"
        )
        header_layout = QHBoxLayout(
            header
        )
        header_layout.setContentsMargins(
            16,
            13,
            16,
            13,
        )

        heading = QVBoxLayout()
        heading.setSpacing(2)

        title = QLabel(
            "Mission Control"
        )
        title.setObjectName(
            "PageTitle"
        )

        subtitle = QLabel(
            "Buster Desktop AI OS — Runtime command center"
        )
        subtitle.setObjectName(
            "MutedText"
        )

        heading.addWidget(title)
        heading.addWidget(subtitle)

        self.refresh_btn = QPushButton(
            "Refresh"
        )
        self.workflow_btn = QPushButton(
            "Run Workflow"
        )
        self.health_btn = QPushButton(
            "Health"
        )

        header_layout.addLayout(
            heading,
            1,
        )
        header_layout.addWidget(
            self.refresh_btn
        )
        header_layout.addWidget(
            self.workflow_btn
        )
        header_layout.addWidget(
            self.health_btn
        )

        root.addWidget(header)
        root.addWidget(
            self._build_status_strip()
        )

        split = QSplitter(
            Qt.Horizontal
        )

        self.nav = QListWidget()
        self.nav.setObjectName(
            "MissionNav"
        )

        for name in (
            "Dashboard",
            "Runtime",
            "Services",
            "Agents",
            "Jobs",
            "Events",
            "Blackboard",
            "Memory",
            "Plugins",
            "Workflow",
        ):
            self.nav.addItem(
                QListWidgetItem(name)
            )

        self.main = QTextEdit()
        self.main.setObjectName(
            "MainView"
        )
        self.main.setReadOnly(True)

        self.inspector = QTextEdit()
        self.inspector.setObjectName(
            "InspectorView"
        )
        self.inspector.setReadOnly(True)

        split.addWidget(self.nav)
        split.addWidget(self.main)
        split.addWidget(
            self.inspector
        )

        split.setStretchFactor(
            0,
            1,
        )
        split.setStretchFactor(
            1,
            4,
        )
        split.setStretchFactor(
            2,
            2,
        )
        split.setSizes(
            [170, 600, 300]
        )

        root.addWidget(
            split,
            1,
        )

    def _build_status_strip(self):
        frame = QFrame()
        frame.setObjectName(
            "AIStatusCard"
        )

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(
            16,
            12,
            16,
            12,
        )
        layout.setSpacing(18)

        self.ai_provider_value = (
            self._metric(
                layout,
                "AI Provider",
                "Unknown",
            )
        )
        self.ai_model_value = (
            self._metric(
                layout,
                "Model",
                "Unknown",
            )
        )
        self.ai_status_value = (
            self._metric(
                layout,
                "Connection",
                "Unavailable",
            )
        )
        self.ai_fallback_value = (
            self._metric(
                layout,
                "Fallback",
                "Local Rules",
            )
        )
        self.repair_status_value = (
            self._metric(
                layout,
                "Repair",
                "Idle",
            )
        )
        self.repair_progress_value = (
            self._metric(
                layout,
                "Progress",
                "0%",
            )
        )

        layout.addStretch()
        return frame

    @staticmethod
    def _metric(
        layout,
        label_text,
        value_text,
    ):
        group = QVBoxLayout()
        group.setSpacing(2)

        label = QLabel(label_text)
        label.setObjectName(
            "MetricLabel"
        )

        value = QLabel(value_text)
        value.setObjectName(
            "MetricValue"
        )

        group.addWidget(label)
        group.addWidget(value)
        layout.addLayout(group)
        return value

    def _connect_signals(self):
        self.nav.currentItemChanged.connect(
            self._on_nav_changed
        )
        self.refresh_btn.clicked.connect(
            self._manual_refresh
        )
        self.workflow_btn.clicked.connect(
            self.run_workflow
        )
        self.health_btn.clicked.connect(
            self.run_health
        )

    def _connect_presenter(self):
        self.presenter.section_changed.connect(
            self._render_section
        )
        self.presenter.ai_changed.connect(
            self._render_ai
        )
        self.presenter.repair_changed.connect(
            self._render_repair
        )
        self.presenter.event_received.connect(
            self._on_runtime_event
        )
        self.presenter.error.connect(
            self._render_error
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    @staticmethod
    def pretty(data):
        return json.dumps(
            data,
            indent=4,
            default=str,
        )

    @Slot(object, object)
    def _on_nav_changed(
        self,
        current,
        _previous,
    ) -> None:
        section = (
            current.text()
            if current is not None
            else "Dashboard"
        )
        self.presenter.set_section(
            section
        )

    @Slot()
    def _manual_refresh(self) -> None:
        self.presenter.refresh_all()

    @Slot(str, object)
    def _render_section(
        self,
        section: str,
        data: Any,
    ) -> None:
        self.main.setPlainText(
            self.pretty(data)
        )
        self.inspector.setPlainText(
            self.pretty(
                self.presenter
                .inspector_data()
            )
        )

    @Slot(object)
    def _render_ai(
        self,
        ai: Any,
    ) -> None:
        if not isinstance(ai, Mapping):
            return

        self.ai_provider_value.setText(
            str(
                ai.get(
                    "provider_label",
                    "Unknown",
                )
            )
        )
        self.ai_model_value.setText(
            str(
                ai.get(
                    "model",
                    "Unknown",
                )
            )
        )

        connected = ai.get(
            "connected"
        )

        if connected is True:
            connection_text = (
                "Connected"
            )
            state = "online"
        elif connected is False:
            connection_text = (
                "Unavailable"
            )
            state = "offline"
        else:
            connection_text = str(
                ai.get(
                    "status",
                    "Configured",
                )
            )
            state = "configured"

        self.ai_status_value.setText(
            connection_text
        )
        self.ai_fallback_value.setText(
            str(
                ai.get(
                    "fallback",
                    "Local Rules",
                )
            )
        )

        self.ai_status_value.setProperty(
            "state",
            state,
        )
        self._repolish(
            self.ai_status_value
        )

    @Slot(object)
    def _render_repair(
        self,
        repair: Any,
    ) -> None:
        if not isinstance(
            repair,
            Mapping,
        ):
            return

        latest = repair.get(
            "latest_session",
            {},
        )

        if isinstance(latest, Mapping):
            latest_state = latest.get(
                "status",
                "idle",
            )
            progress = latest.get(
                "progress_percent",
                0,
            )
        else:
            latest_state = (
                repair.get(
                    "state",
                    "idle",
                )
            )
            progress = repair.get(
                "progress_percent",
                0,
            )

        state_text = str(
            repair.get(
                "title",
                latest_state,
            )
            or "idle"
        ).replace(
            "_",
            " ",
        ).title()

        self.repair_status_value.setText(
            state_text
        )
        self.repair_progress_value.setText(
            f"{int(progress or 0)}%"
        )

        if str(latest_state).lower() in {
            "failed",
            "verification_failed",
            "recovery_required",
        }:
            state = "offline"
        elif str(latest_state).lower() in {
            "completed",
            "verified",
            "ready",
        }:
            state = "online"
        else:
            state = "configured"

        self.repair_status_value.setProperty(
            "state",
            state,
        )
        self._repolish(
            self.repair_status_value
        )

    @Slot(object)
    def _on_runtime_event(
        self,
        _event: Any,
    ) -> None:
        # The presenter has already updated its local state.
        # Re-rendering is driven by section_changed.
        pass

    @Slot(str)
    def _render_error(
        self,
        message: str,
    ) -> None:
        self.main.setPlainText(
            f"Mission Control error:\n\n{message}"
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def refresh(self, *_args):
        """
        Compatibility entry point for existing callers.

        No timer calls this method. It performs an explicit manual refresh.
        """
        self.presenter.refresh_all()

    def run_workflow(self):
        try:
            self.presenter.run_workflow()
        except Exception as exc:
            self._render_error(str(exc))

    def run_health(self):
        try:
            self.presenter.run_health()
        except Exception as exc:
            self._render_error(str(exc))

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        presenter = getattr(
            self,
            "presenter",
            None,
        )

        if presenter is not None:
            presenter.close()

    def closeEvent(
        self,
        event,
    ) -> None:
        self.shutdown()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget#MissionControlV12 {
                background: #0b1018;
                color: #e8edf5;
            }

            QFrame#HeaderCard,
            QFrame#AIStatusCard {
                background: #111925;
                border: 1px solid #243247;
                border-radius: 11px;
            }

            QLabel#PageTitle {
                color: #f4f7fb;
                font-size: 22px;
                font-weight: 700;
            }

            QLabel#MutedText {
                color: #8fa0b7;
                font-size: 12px;
            }

            QLabel#MetricLabel {
                color: #7f91aa;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel#MetricValue {
                color: #dce8f7;
                font-size: 14px;
                font-weight: 700;
            }

            QLabel#MetricValue[state="online"] {
                color: #8fe0aa;
            }

            QLabel#MetricValue[state="offline"] {
                color: #ff9f9f;
            }

            QLabel#MetricValue[state="configured"] {
                color: #eacb7c;
            }

            QListWidget#MissionNav,
            QTextEdit#MainView,
            QTextEdit#InspectorView {
                background: #0d1520;
                color: #e5ebf4;
                border: 1px solid #27364b;
                border-radius: 9px;
            }

            QListWidget#MissionNav {
                padding: 6px;
                outline: none;
            }

            QListWidget#MissionNav::item {
                padding: 9px 10px;
                border-radius: 6px;
            }

            QListWidget#MissionNav::item:selected {
                background: #24476c;
                color: white;
            }

            QTextEdit#MainView,
            QTextEdit#InspectorView {
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
                padding: 7px;
            }

            QPushButton {
                color: #dce6f3;
                background: #172231;
                border: 1px solid #2e4058;
                border-radius: 7px;
                padding: 8px 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #1c2b3e;
                border-color: #426184;
            }

            QSplitter::handle {
                background: #182231;
                width: 3px;
            }
            """
        )

    @staticmethod
    def _repolish(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


__all__ = [
    "MissionControlEventBridge",
    "MissionControlPresenter",
    "MissionControlState",
    "MissionControlV12",
]
