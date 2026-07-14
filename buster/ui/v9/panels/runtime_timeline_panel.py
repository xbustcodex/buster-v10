from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TimelineEventCard(QFrame):
    EVENT_COLORS = {
        "runtime": "#23B8FF",
        "job": "#7A8CFF",
        "agent": "#31D158",
        "vision": "#20E3B2",
        "voice": "#54D7FF",
        "notification": "#FFBF2F",
        "face": "#FF8A65",
        "memory": "#C084FC",
        "workspace": "#F59E0B",
        "plugin": "#EC4899",
        "default": "#8393A8",
    }

    EVENT_ICONS = {
        "runtime": "⚙",
        "job": "📋",
        "agent": "🤖",
        "vision": "👁",
        "voice": "🎤",
        "notification": "🔔",
        "face": "😊",
        "memory": "🧠",
        "workspace": "📁",
        "plugin": "🔌",
        "default": "•",
    }

    def __init__(
        self,
        event: Dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)

        event_type = str(event.get("type", "unknown"))
        category = event_type.split(".")[0]
        payload = event.get("payload", {})

        if not isinstance(payload, dict):
            payload = {}

        color = self.EVENT_COLORS.get(
            category,
            self.EVENT_COLORS["default"],
        )

        icon = self.EVENT_ICONS.get(
            category,
            self.EVENT_ICONS["default"],
        )

        self.setObjectName("TimelineEventCard")
        self.setStyleSheet(
            f"""
            QFrame#TimelineEventCard {{
                background:#081321;
                border:1px solid {color};
                border-radius:12px;
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)

        header = QHBoxLayout()

        event_label = QLabel(
            f"{icon}  {self._format_event_type(event_type)}"
        )
        event_label.setStyleSheet(
            f"color:{color};font-size:15px;font-weight:700;"
        )

        time_label = QLabel(
            self._format_time(
                str(event.get("created_at", ""))
            )
        )
        time_label.setStyleSheet(
            "color:#7188A5;font-size:11px;"
        )

        header.addWidget(event_label)
        header.addStretch()
        header.addWidget(time_label)

        source_label = QLabel(
            f"Source: {event.get('source', 'runtime')}"
        )
        source_label.setStyleSheet(
            "color:#8EA4BF;font-size:11px;"
        )

        message_label = QLabel(
            self._event_message(
                event_type,
                payload,
            )
        )
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        message_label.setStyleSheet(
            "color:#DCE8F8;font-size:13px;"
        )

        root.addLayout(header)
        root.addWidget(source_label)
        root.addWidget(message_label)

    def _format_event_type(self, event_type: str) -> str:
        return event_type.replace(".", " ").replace("_", " ").title()

    def _format_time(self, value: str) -> str:
        if not value:
            return datetime.now().strftime("%H:%M:%S")

        try:
            cleaned = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed.strftime("%H:%M:%S")
        except Exception:
            return value[-8:] if len(value) >= 8 else value

    def _event_message(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> str:
        if event_type in {
            "runtime.started",
            "runtime.core.started",
        }:
            return (
                f"Runtime started at "
                f"{payload.get('root', 'project root')}."
            )

        if event_type in {
            "runtime.stopped",
            "runtime.core.stopped",
        }:
            return "Runtime stopped."

        if event_type in {
            "runtime.request",
            "runtime.core.request.received",
        }:
            return str(
                payload.get(
                    "request",
                    "Runtime request received.",
                )
            )

        if event_type == "job.created":
            return (
                f"Created job: "
                f"{payload.get('title') or payload.get('name') or payload.get('job_type', 'Unknown')}"
            )

        if event_type == "job.started":
            return (
                f"Started job: "
                f"{payload.get('title') or payload.get('job') or payload.get('job_id', 'Unknown')}"
            )

        if event_type == "job.progress":
            return (
                f"{payload.get('job', 'Job')} — "
                f"{payload.get('progress', 0)}% complete"
            )

        if event_type == "job.finished":
            return (
                f"Job completed: "
                f"{payload.get('job_id', 'Unknown')}"
            )

        if event_type == "job.failed":
            return str(
                payload.get(
                    "error",
                    "Runtime job failed.",
                )
            )

        if event_type == "agent.started":
            return (
                f"{str(payload.get('agent', 'Agent')).title()} "
                f"Agent started."
            )

        if event_type == "agent.finished":
            return (
                f"{str(payload.get('agent', 'Agent')).title()} "
                f"Agent completed."
            )

        if event_type == "agent.failed":
            return (
                f"{str(payload.get('agent', 'Agent')).title()} "
                f"Agent failed: "
                f"{payload.get('error', 'Unknown error')}"
            )

        if event_type == "vision.camera.started":
            return (
                f"Camera {payload.get('camera_id', 0)} started "
                f"in {payload.get('mode', 'normal')} mode."
            )

        if event_type == "vision.camera.stopped":
            return "Vision camera stopped."

        if event_type == "vision.face.detected":
            count = int(payload.get("count", 0))
            return (
                f"Detected {count} face"
                f"{'' if count == 1 else 's'}."
            )

        if event_type == "vision.qr.detected":
            count = int(payload.get("count", 0))
            return (
                f"Detected {count} QR code"
                f"{'' if count == 1 else 's'}."
            )

        if event_type == "voice.status":
            return (
                f"Voice status changed to "
                f"{payload.get('status', 'unknown')}."
            )

        if event_type == "voice.transcribed":
            return (
                f'Transcribed: "{str(payload.get("text", ""))[:160]}"'
            )

        if event_type == "notification":
            return (
                f"{payload.get('title', 'Buster')}: "
                f"{payload.get('message', '')}"
            )

        if event_type == "face.state":
            return (
                f"Face changed to "
                f"{payload.get('state', 'idle')}: "
                f"{payload.get('message', '')}"
            )

        if payload:
            important_keys = [
                "title",
                "message",
                "status",
                "request",
                "agent",
                "job_id",
                "mode",
                "path",
                "error",
            ]

            parts = []

            for key in important_keys:
                if key in payload:
                    parts.append(
                        f"{key}: {payload[key]}"
                    )

            if parts:
                return " • ".join(parts)

            return str(payload)[:300]

        return "Runtime event received."


class RuntimeTimelinePanel(QWidget):
    runtime_event_signal = Signal(dict)

    def __init__(
        self,
        live=None,
        runtime_core=None,
        parent=None,
    ):
        super().__init__(parent)

        self.live = live
        self.runtime_core = runtime_core

        self._subscribed = False
        self._events: list[Dict[str, Any]] = []
        self._maximum_events = 500

        self.setWindowTitle("Buster Runtime Timeline")
        self.resize(900, 760)

        self.setStyleSheet(
            """
            QWidget {
                background:#050B14;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }

            QListWidget {
                background:#050B14;
                border:none;
                outline:none;
            }

            QListWidget::item {
                border:none;
                padding:4px;
            }

            QComboBox,
            QPushButton {
                background:#0A1D33;
                color:#DCEBFF;
                border:1px solid #175A94;
                border-radius:8px;
                padding:8px 12px;
                font-weight:600;
            }

            QComboBox:hover,
            QPushButton:hover {
                background:#0E2A49;
                border-color:#23B8FF;
            }

            QComboBox QAbstractItemView {
                background:#081321;
                color:#DCEBFF;
                selection-background-color:#0E2A49;
            }
            """
        )

        self._build_ui()

        self.runtime_event_signal.connect(
            self._handle_runtime_event
        )

        self._connect_dispatcher()
        self.reload_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()

        title_box = QVBoxLayout()

        title = QLabel("LIVE RUNTIME TIMELINE")
        title.setStyleSheet(
            "font-size:25px;font-weight:800;color:#23B8FF;"
        )

        subtitle = QLabel(
            "Runtime, jobs, agents, voice, vision and system activity"
        )
        subtitle.setStyleSheet(
            "font-size:12px;color:#7894B5;"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.count_label = QLabel("0 events")
        self.count_label.setStyleSheet(
            "color:#9FB8D5;font-weight:600;"
        )

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "All Events",
                "Runtime",
                "Jobs",
                "Agents",
                "Vision",
                "Voice",
                "Notifications",
                "Face",
                "Memory",
                "Workspace",
                "Plugins",
            ]
        )
        self.filter_combo.currentTextChanged.connect(
            self.apply_filter
        )

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(
            self.reload_history
        )

        clear_button = QPushButton("Clear View")
        clear_button.clicked.connect(
            self.clear_view
        )

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(self.count_label)
        header.addWidget(self.filter_combo)
        header.addWidget(reload_button)
        header.addWidget(clear_button)

        self.timeline_list = QListWidget()
        self.timeline_list.setSpacing(5)

        root.addLayout(header)
        root.addWidget(self.timeline_list, 1)

    def _connect_dispatcher(self) -> None:
        if self._subscribed or not self.runtime_core:
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )

        if dispatcher is None:
            return

        dispatcher.subscribe(
            "*",
            self._receive_runtime_event,
        )

        self._subscribed = True

    def _disconnect_dispatcher(self) -> None:
        if not self._subscribed or not self.runtime_core:
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )

        if dispatcher is not None:
            dispatcher.unsubscribe(
                "*",
                self._receive_runtime_event,
            )

        self._subscribed = False

    def _receive_runtime_event(
        self,
        event: Dict[str, Any],
    ) -> None:
        self.runtime_event_signal.emit(event)

    @Slot(dict)
    def _handle_runtime_event(
        self,
        event: Dict[str, Any],
    ) -> None:
        self._events.append(event)

        if len(self._events) > self._maximum_events:
            self._events = self._events[
                -self._maximum_events:
            ]

        if self._event_matches_filter(event):
            self._insert_event(event)

        self._update_count()

    def _insert_event(
        self,
        event: Dict[str, Any],
    ) -> None:
        card = TimelineEventCard(event)

        item = QListWidgetItem()
        item.setSizeHint(card.sizeHint())

        self.timeline_list.insertItem(0, item)
        self.timeline_list.setItemWidget(
            item,
            card,
        )

    def reload_history(self) -> None:
        self.timeline_list.clear()
        self._events.clear()

        if not self.runtime_core:
            self._update_count()
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )

        if dispatcher is None:
            self._update_count()
            return

        self._events = dispatcher.history()[
            -self._maximum_events:
        ]

        for event in reversed(self._events):
            if self._event_matches_filter(event):
                self._insert_event(event)

        self._update_count()

    def clear_view(self) -> None:
        self.timeline_list.clear()
        self._events.clear()
        self._update_count()

    def apply_filter(self) -> None:
        self.timeline_list.clear()

        for event in reversed(self._events):
            if self._event_matches_filter(event):
                self._insert_event(event)

        self._update_count()

    def _event_matches_filter(
        self,
        event: Dict[str, Any],
    ) -> bool:
        selected = self.filter_combo.currentText()

        if selected == "All Events":
            return True

        event_type = str(
            event.get("type", "")
        )

        prefixes = {
            "Runtime": "runtime.",
            "Jobs": "job.",
            "Agents": "agent.",
            "Vision": "vision.",
            "Voice": "voice.",
            "Notifications": "notification",
            "Face": "face.",
            "Memory": "memory.",
            "Workspace": "workspace.",
            "Plugins": "plugin.",
        }

        prefix = prefixes.get(selected)

        if prefix is None:
            return True

        return event_type.startswith(prefix)

    def _update_count(self) -> None:
        visible = self.timeline_list.count()
        total = len(self._events)

        self.count_label.setText(
            f"{visible} shown / {total} total"
        )

    def closeEvent(self, event) -> None:
        self._disconnect_dispatcher()
        event.accept()