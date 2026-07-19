from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class RuntimeEventCard(QFrame):
    """
    Reusable timeline card for one runtime event.

    Expected event format:

    {
        "id": 12,
        "type": "job.finished",
        "source": "runtime_core",
        "payload": {...},
        "created_at": "2026-07-15T10:20:31+00:00",
    }
    """

    CATEGORY_COLORS = {
        "runtime": "#23B8FF",
        "orchestrator": "#7A8CFF",
        "workflow": "#7A8CFF",
        "job": "#FFBF2F",
        "agent": "#31D158",
        "tester": "#31D158",
        "builder": "#31D158",
        "reviewer": "#31D158",
        "fixer": "#FF8A65",
        "planner": "#C084FC",
        "vision": "#20E3B2",
        "voice": "#54D7FF",
        "chat": "#62A8FF",
        "face": "#FF8A65",
        "notification": "#FFBF2F",
        "memory": "#C084FC",
        "workspace": "#F59E0B",
        "plugin": "#EC4899",
        "registry": "#8393A8",
        "default": "#8393A8",
    }

    CATEGORY_ICONS = {
        "runtime": "⚙",
        "orchestrator": "🧭",
        "workflow": "🔀",
        "job": "📋",
        "agent": "🤖",
        "tester": "🧪",
        "builder": "🔨",
        "reviewer": "🔍",
        "fixer": "🛠",
        "planner": "🧠",
        "vision": "👁",
        "voice": "🎤",
        "chat": "💬",
        "face": "😊",
        "notification": "🔔",
        "memory": "🧠",
        "workspace": "📁",
        "plugin": "🔌",
        "registry": "📚",
        "default": "•",
    }

    def __init__(
        self,
        event: Dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)

        self.runtime_event = (
            event if isinstance(event, dict) else {}
        )

        self.event_type = str(
            self.runtime_event.get("type", "unknown")
        )
        self.source = str(
            self.runtime_event.get("source", "runtime")
        )
        self.payload = self.runtime_event.get("payload", {})

        if not isinstance(self.payload, dict):
            self.payload = {
                "value": self.payload,
            }

        self.category = self._detect_category(
            self.event_type,
            self.source,
        )

        self.color = self.CATEGORY_COLORS.get(
            self.category,
            self.CATEGORY_COLORS["default"],
        )

        self.icon = self.CATEGORY_ICONS.get(
            self.category,
            self.CATEGORY_ICONS["default"],
        )

        self._expanded = False

        self.setObjectName("RuntimeEventCard")
        
        self.setStyleSheet(
            f"""
            QFrame#RuntimeEventCard {{
                background: #081321;
                border: 1px solid {self.color};
                border-radius: 12px;
            }}

            QLabel {{
                background: transparent;
                border: none;
            }}

            QPushButton {{
                background: #0A1D33;
                color: #DCEBFF;
                border: 1px solid #175A94;
                border-radius: 7px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                background: #0E2A49;
                border-color: #23B8FF;
            }}

            QTextEdit {{
                background: #050B14;
                color: #BFD1E7;
                border: 1px solid #14324F;
                border-radius: 8px;
                padding: 7px;
                font-family: "Consolas";
                font-size: 11px;
            }}
            """
        )

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(7)

        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_label = QLabel(
            f"{self.icon}  {self._format_event_type(self.event_type)}"
        )
        self.title_label.setStyleSheet(
            f"""
            color: {self.color};
            font-size: 15px;
            font-weight: 700;
            """
        )

        self.time_label = QLabel(
            self._format_time(
                str(self.runtime_event.get("created_at", ""))
            )
        )
        self.time_label.setStyleSheet(
            "color: #7188A5; font-size: 11px;"
        )

        self.expand_button = QPushButton("Details")
        self.expand_button.setFixedWidth(72)
        self.expand_button.clicked.connect(
            self.toggle_details
        )

        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.time_label)
        header.addWidget(self.expand_button)

        metadata = QHBoxLayout()

        event_id = self.runtime_event.get("id")

        event_id_text = (
            f"Event #{event_id}"
            if event_id is not None
            else "Event"
        )

        self.id_label = QLabel(event_id_text)
        self.id_label.setStyleSheet(
            "color: #7F95AF; font-size: 10px;"
        )

        self.source_label = QLabel(
            f"Source: {self.source}"
        )
        self.source_label.setStyleSheet(
            "color: #8EA4BF; font-size: 10px;"
        )

        self.type_label = QLabel(
            self.event_type
        )
        self.type_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        self.type_label.setStyleSheet(
            f"""
            color: {self.color};
            border: 1px solid {self.color};
            border-radius: 6px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: 600;
            """
        )

        metadata.addWidget(self.id_label)
        metadata.addWidget(self.source_label)
        metadata.addStretch()
        metadata.addWidget(self.type_label)

        self.message_label = QLabel(
            self._build_summary()
        )
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        self.message_label.setStyleSheet(
            "color: #DCE8F8; font-size: 13px;"
        )

        self.details_box = QTextEdit()
        self.details_box.setReadOnly(True)
        self.details_box.setVisible(False)
        self.details_box.setMinimumHeight(90)
        self.details_box.setMaximumHeight(220)
        self.details_box.setPlainText(
            self._format_payload(self.payload)
        )

        root.addLayout(header)
        root.addLayout(metadata)
        root.addWidget(self.message_label)
        root.addWidget(self.details_box)

    def toggle_details(self) -> None:
        self._expanded = not self._expanded
        self.details_box.setVisible(self._expanded)
        self.expand_button.setText(
            "Hide"
            if self._expanded
            else "Details"
        )

        self.updateGeometry()

    def _detect_category(
        self,
        event_type: str,
        source: str,
    ) -> str:
        prefix = event_type.split(".", 1)[0].lower()

        if prefix in self.CATEGORY_COLORS:
            return prefix

        source_lower = source.lower()

        for category in self.CATEGORY_COLORS:
            if category == "default":
                continue

            if category in source_lower:
                return category

        return "default"

    def _format_event_type(
        self,
        event_type: str,
    ) -> str:
        return (
            event_type
            .replace(".", " ")
            .replace("_", " ")
            .strip()
            .title()
        )

    def _format_time(
        self,
        value: str,
    ) -> str:
        if not value:
            return datetime.now().strftime(
                "%H:%M:%S"
            )

        try:
            cleaned = value.replace(
                "Z",
                "+00:00",
            )

            parsed = datetime.fromisoformat(
                cleaned
            )

            return parsed.strftime(
                "%H:%M:%S"
            )

        except Exception:
            return (
                value[-8:]
                if len(value) >= 8
                else value
            )

    def _build_summary(self) -> str:
        event_type = self.event_type
        payload = self.payload

        if event_type in {
            "runtime.started",
            "runtime.core.started",
        }:
            root = payload.get(
                "root",
                "project root",
            )
            return f"Runtime started at {root}."

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

        if event_type == "runtime.tick":
            return "Runtime heartbeat tick completed."

        if event_type == "orchestrator.started":
            agents = payload.get(
                "agents",
                [],
            )

            if isinstance(agents, list):
                agent_text = ", ".join(
                    str(agent).title()
                    for agent in agents
                )
            else:
                agent_text = str(agents)

            return (
                f"Orchestrator started for "
                f"{payload.get('request', 'request')}."
                + (
                    f" Agents: {agent_text}."
                    if agent_text
                    else ""
                )
            )

        if event_type == "orchestrator.finished":
            return (
                f"Orchestrator finished with status "
                f"{payload.get('status', 'completed')}."
            )

        if event_type == "orchestrator.failed":
            return str(
                payload.get(
                    "error",
                    "Orchestrator failed.",
                )
            )

        if event_type == "orchestrator.step.started":
            return (
                f"Started step "
                f"{payload.get('step', '?')}: "
                f"{payload.get('title', 'Workflow step')}."
            )

        if event_type == "orchestrator.step.finished":
            return (
                f"Completed step "
                f"{payload.get('step', '?')}: "
                f"{payload.get('title', 'Workflow step')}."
            )

        if event_type == "orchestrator.step.failed":
            return (
                f"Step {payload.get('step', '?')} failed: "
                f"{payload.get('title', 'Workflow step')}."
            )

        if event_type == "workflow.started":
            return (
                f"Workflow started with "
                f"{payload.get('steps', 0)} planned steps."
            )

        if event_type == "workflow.finished":
            return (
                f"Workflow finished with status "
                f"{payload.get('status', 'completed')}."
            )

        if event_type == "job.created":
            title = (
                payload.get("title")
                or payload.get("name")
                or payload.get("job_type")
                or "Unknown job"
            )

            return f"Created job: {title}"

        if event_type == "job.started":
            title = (
                payload.get("title")
                or payload.get("job")
                or payload.get("job_id")
                or "Unknown job"
            )

            return f"Started job: {title}"

        if event_type == "job.progress":
            progress = payload.get(
                "progress",
                0,
            )

            return (
                f"{payload.get('job', 'Job')} "
                f"is {progress}% complete."
            )

        if event_type == "job.finished":
            return (
                f"Job {payload.get('job_id', 'Unknown')} "
                f"completed successfully."
            )

        if event_type == "job.failed":
            return str(
                payload.get(
                    "error",
                    "Runtime job failed.",
                )
            )

        if event_type == "agent.started":
            agent = str(
                payload.get(
                    "agent",
                    "Agent",
                )
            )

            return f"{agent.title()} Agent started."

        if event_type == "agent.finished":
            agent = str(
                payload.get(
                    "agent",
                    "Agent",
                )
            )

            return f"{agent.title()} Agent completed."

        if event_type == "agent.failed":
            agent = str(
                payload.get(
                    "agent",
                    "Agent",
                )
            )

            error = payload.get(
                "error",
                "Unknown error",
            )

            return (
                f"{agent.title()} Agent failed: "
                f"{error}"
            )

        if event_type == "tester.completed":
            status = str(
                payload.get(
                    "status",
                    "unknown",
                )
            )

            summary = (
                payload.get("summary")
                or payload.get("message")
                or payload.get("output_tail")
                or "Testing completed."
            )

            return (
                f"Tester status: {status}. "
                f"{str(summary)[:220]}"
            )

        if event_type == "vision.camera.started":
            return (
                f"Camera {payload.get('camera_id', 0)} "
                f"started in "
                f"{payload.get('mode', 'normal')} mode."
            )

        if event_type == "vision.camera.stopped":
            return "Vision camera stopped."

        if event_type == "vision.mode.changed":
            return (
                f"Vision mode changed to "
                f"{payload.get('mode', 'normal')}."
            )

        if event_type == "vision.face.detected":
            count = self._safe_int(
                payload.get("count", 0)
            )

            return (
                f"Detected {count} face"
                f"{'' if count == 1 else 's'}."
            )

        if event_type == "vision.qr.detected":
            count = self._safe_int(
                payload.get("count", 0)
            )

            return (
                f"Detected {count} QR code"
                f"{'' if count == 1 else 's'}."
            )

        if event_type == "vision.objects.detected":
            count = self._safe_int(
                payload.get("count", 0)
            )

            return (
                f"Detected {count} object"
                f"{'' if count == 1 else 's'}."
            )

        if event_type == "vision.photo.saved":
            return (
                f"Vision photo saved to "
                f"{payload.get('path', 'unknown path')}."
            )

        if event_type == "voice.status":
            return (
                f"Voice status changed to "
                f"{payload.get('status', 'unknown')}."
            )

        if event_type == "voice.transcribed":
            text = str(
                payload.get(
                    "text",
                    "",
                )
            )

            return f'Transcribed: "{text[:180]}"'

        if event_type == "chat.message.received":
            return str(
                payload.get(
                    "text",
                    "Chat message received.",
                )
            )

        if event_type == "chat.message.completed":
            return str(
                payload.get(
                    "text",
                    "Chat response completed.",
                )
            )[:260]

        if event_type == "chat.message.failed":
            return str(
                payload.get(
                    "error",
                    "Chat request failed.",
                )
            )

        if event_type == "notification":
            title = payload.get(
                "title",
                "Buster",
            )

            message = payload.get(
                "message",
                "",
            )

            return f"{title}: {message}"

        if event_type == "face.state":
            state = payload.get(
                "state",
                "idle",
            )

            message = payload.get(
                "message",
                "",
            )

            return (
                f"Face changed to {state}."
                + (
                    f" {message}"
                    if message
                    else ""
                )
            )

        if event_type == "memory.updated":
            return (
                f"Memory updated by "
                f"{payload.get('agent', 'runtime')}."
            )

        if event_type == "workspace.changed":
            workspace = (
                payload.get("path")
                or payload.get("workspace")
                or "workspace update"
            )

            return f"Workspace changed: {workspace}."

        if event_type == "plugin.loaded":
            return (
                f"Plugin loaded: "
                f"{payload.get('plugin', 'unknown')}."
            )

        if event_type == "plugin.unloaded":
            return (
                f"Plugin unloaded: "
                f"{payload.get('plugin', 'unknown')}."
            )

        return self._generic_summary(payload)

    def _generic_summary(
        self,
        payload: Dict[str, Any],
    ) -> str:
        if not payload:
            return "Runtime event received."

        preferred_keys = (
            "message",
            "summary",
            "status",
            "request",
            "title",
            "agent",
            "job_id",
            "mode",
            "path",
            "error",
        )

        parts = []

        for key in preferred_keys:
            value = payload.get(key)

            if value in (
                None,
                "",
                [],
                {},
            ):
                continue

            parts.append(
                f"{key.replace('_', ' ').title()}: "
                f"{self._compact_value(value)}"
            )

        if parts:
            return " • ".join(parts[:4])

        return self._compact_value(payload)

    def _compact_value(
        self,
        value: Any,
    ) -> str:
        text = str(value)
        text = " ".join(
            text.split()
        )

        if len(text) > 280:
            return text[:277] + "..."

        return text

    def _format_payload(
        self,
        payload: Dict[str, Any],
    ) -> str:
        try:
            import json

            return json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        except Exception:
            return str(payload)

    def _safe_int(
        self,
        value: Any,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0