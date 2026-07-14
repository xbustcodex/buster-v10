from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NotificationCard(QFrame):
    LEVEL_COLORS = {
        "info": "#23B8FF",
        "success": "#31D158",
        "warning": "#FFB020",
        "error": "#FF5C5C",
        "danger": "#FF5C5C",
    }

    def __init__(
        self,
        title: str,
        message: str,
        level: str = "info",
        created_at: str | None = None,
        source: str = "runtime",
        parent=None,
    ):
        super().__init__(parent)

        level = str(level or "info").lower()
        color = self.LEVEL_COLORS.get(level, "#23B8FF")

        self.setStyleSheet(
            f"""
            QFrame {{
                background: #081321;
                border: 1px solid {color};
                border-radius: 12px;
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(5)

        header = QHBoxLayout()

        title_label = QLabel(title or "Buster")
        title_label.setStyleSheet(
            f"color:{color};font-size:15px;font-weight:700;"
        )

        level_label = QLabel(level.upper())
        level_label.setStyleSheet(
            f"""
            color:{color};
            border:1px solid {color};
            border-radius:7px;
            padding:2px 7px;
            font-size:10px;
            font-weight:700;
            """
        )

        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(level_label)

        message_label = QLabel(message or "")
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        message_label.setStyleSheet(
            "color:#DCE8F8;font-size:13px;"
        )

        footer = QLabel(
            f"{created_at or datetime.now().isoformat(timespec='seconds')}"
            f"  •  {source}"
        )
        footer.setStyleSheet(
            "color:#7188A5;font-size:10px;"
        )

        root.addLayout(header)
        root.addWidget(message_label)
        root.addWidget(footer)


class NotificationCenterPanel(QWidget):
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
        self._notifications: list[Dict[str, Any]] = []

        self.setWindowTitle("Buster Notification Center")
        self.resize(760, 720)

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

            QPushButton {
                background:#0A1D33;
                color:#DCEBFF;
                border:1px solid #175A94;
                border-radius:8px;
                padding:8px 13px;
                font-weight:600;
            }

            QPushButton:hover {
                background:#0E2A49;
                border-color:#23B8FF;
            }
            """
        )

        self._build_ui()

        self.runtime_event_signal.connect(
            self._handle_runtime_event
        )

        self._connect_dispatcher()
        self._load_dispatcher_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()

        title_box = QVBoxLayout()

        title = QLabel("NOTIFICATION CENTER")
        title.setStyleSheet(
            "font-size:25px;font-weight:800;color:#23B8FF;"
        )

        subtitle = QLabel(
            "Live runtime, agent, voice, vision and job alerts"
        )
        subtitle.setStyleSheet(
            "font-size:12px;color:#7894B5;"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.count_label = QLabel("0 notifications")
        self.count_label.setStyleSheet(
            "color:#9FB8D5;font-weight:600;"
        )

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_notifications)

        refresh_button = QPushButton("Reload")
        refresh_button.clicked.connect(
            self._load_dispatcher_history
        )

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(self.count_label)
        header.addWidget(refresh_button)
        header.addWidget(clear_button)

        self.notification_list = QListWidget()
        self.notification_list.setSpacing(5)

        root.addLayout(header)
        root.addWidget(self.notification_list, 1)

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
            "notification",
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
                "notification",
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
        if event.get("type") != "notification":
            return

        payload = event.get("payload", {})

        if not isinstance(payload, dict):
            payload = {}

        notification = {
            "title": str(
                payload.get("title", "Buster")
            ),
            "message": str(
                payload.get("message", "")
            ),
            "level": str(
                payload.get("level", "info")
            ),
            "created_at": str(
                event.get("created_at", "")
            ),
            "source": str(
                event.get("source", "runtime")
            ),
        }

        self.add_notification(notification)

    def add_notification(
        self,
        notification: Dict[str, Any],
    ) -> None:
        self._notifications.append(notification)

        card = NotificationCard(
            title=notification.get("title", "Buster"),
            message=notification.get("message", ""),
            level=notification.get("level", "info"),
            created_at=notification.get("created_at"),
            source=notification.get("source", "runtime"),
        )

        item = QListWidgetItem()
        item.setSizeHint(card.sizeHint())

        self.notification_list.insertItem(0, item)
        self.notification_list.setItemWidget(item, card)

        self._update_count()

    def _load_dispatcher_history(self) -> None:
        self.notification_list.clear()
        self._notifications.clear()

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

        for event in dispatcher.history():
            if event.get("type") != "notification":
                continue

            payload = event.get("payload", {})

            if not isinstance(payload, dict):
                payload = {}

            self.add_notification(
                {
                    "title": str(
                        payload.get("title", "Buster")
                    ),
                    "message": str(
                        payload.get("message", "")
                    ),
                    "level": str(
                        payload.get("level", "info")
                    ),
                    "created_at": str(
                        event.get("created_at", "")
                    ),
                    "source": str(
                        event.get("source", "runtime")
                    ),
                }
            )

        self._update_count()

    def clear_notifications(self) -> None:
        self.notification_list.clear()
        self._notifications.clear()
        self._update_count()

    def _update_count(self) -> None:
        count = len(self._notifications)

        self.count_label.setText(
            f"{count} notification"
            f"{'' if count == 1 else 's'}"
        )

    def closeEvent(self, event) -> None:
        self._disconnect_dispatcher()
        event.accept()