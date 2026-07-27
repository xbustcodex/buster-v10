# buster/ui/v9/chat_view.py
from __future__ import annotations

import inspect
from typing import Any, Callable

from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


CONVERSATIONAL_GREETINGS = {
    "hello",
    "hi",
    "hey",
    "hello buster",
    "hi buster",
    "hey buster",
    "how are you",
    "who are you",
    "ping",
    "good morning",
    "good evening",
}

REPAIR_KEYWORDS = (
    "upgrade",
    "fix",
    "repair",
    "refactor",
    "improve",
    "change",
    "modify",
    "update",
)


class ChatCard(QFrame):
    def __init__(self, text: str, is_user: bool = False):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        top = QHBoxLayout()
        who = QLabel("👤  You" if is_user else "🤖  Buster")
        who.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#20a8ff;"
        )

        timestamp = QLabel(QTime.currentTime().toString("hh:mm:ss AP"))
        timestamp.setObjectName("Small")

        top.addWidget(who)
        top.addStretch()
        top.addWidget(timestamp)
        layout.addLayout(top)

        body = QLabel(str(text))
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet("font-size:14px; color:#dcecff;")
        layout.addWidget(body)

        if not is_user:
            actions = QHBoxLayout()
            for label in ("Copy", "Save", "Open Folder"):
                actions.addWidget(QPushButton(label))
            actions.addStretch()
            layout.addLayout(actions)


class ChatView(QWidget):
    """
    Chat UI connected to the single application-owned runtime.

    ChatView must never construct a SelfImprovementService, repair handler,
    event bus, runtime core, or file writer. All repair work is delegated to
    the service already owned and configured by runtime_core.
    """

    def __init__(
        self,
        live: Any,
        on_message: Callable[[], None] | None = None,
        on_state: Callable[[str], None] | None = None,
        runtime_core: Any = None,
        **kwargs: Any,
    ):
        super().__init__()

        self.live = live
        self.on_message = on_message
        self.on_state = on_state
        self.runtime_core = runtime_core

        if self.runtime_core is None:
            raise RuntimeError(
                "ChatView requires the application runtime_core. "
                "It must not create a separate runtime."
            )

        self.repair_service = self._resolve_repair_service()
        self.build()

    def _resolve_repair_service(self) -> Any:
        """
        Resolve the single runtime-owned repair workflow.

        Chat must never fall back to runtime_core.self_improvement because that
        attribute belongs to the autonomy subsystem, not the repair workflow.
        """
        service = getattr(self.runtime_core, "repair_service", None)
        if service is not None:
            return service

        for attribute in (
            "self_improvement_service",
            "self_improvement_runtime",
        ):
            service = getattr(self.runtime_core, attribute, None)
            if service is not None:
                return service

        raise RuntimeError(
            "BusterRuntimeCore did not initialize the unified repair workflow."
        )

    def build(self) -> None:
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        title = QLabel("Conversation")
        title.setObjectName("Title")

        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(clear)
        layout.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.inner = QWidget()
        self.cards = QVBoxLayout(self.inner)
        self.cards.setSpacing(14)
        self.cards.addStretch()

        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

        row = QHBoxLayout()

        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "Type a command or message (e.g. upgrade the sidebar)..."
        )
        self.input.returnPressed.connect(self.send)

        send_button = QPushButton("Send")
        send_button.setMinimumWidth(110)
        send_button.clicked.connect(self.send)

        row.addWidget(self.input, 1)
        row.addWidget(send_button)
        layout.addLayout(row)

        self.add_card("workspace snapshot", True)
        snapshot = self.live.safe(
            lambda: self.live.brain("workspace snapshot"),
            "Buster v9 ready.",
        )
        self.add_card(snapshot, False)

    def add_card(self, text: Any, is_user: bool = False) -> None:
        self.cards.insertWidget(
            self.cards.count() - 1,
            ChatCard(str(text), is_user),
        )
        QTimer.singleShot(
            0,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            ),
        )

    def _set_state(self, state: str) -> None:
        if self.on_state:
            self.on_state(state)

    @staticmethod
    def _looks_like_repair_request(text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in REPAIR_KEYWORDS)

    def _invoke_with_supported_arguments(
        self,
        func: Callable[..., Any],
        user_message: str,
    ) -> Any:
        """
        Call a runtime repair entry point using only parameters it supports.

        No target file is guessed and auto-approval is deliberately disabled.
        The repair workflow must resolve scope, produce a preview, and apply
        only through its own configured approval policy.
        """
        signature = inspect.signature(func)
        parameters = signature.parameters

        values = {
            "request": user_message,
            "instruction": user_message,
            "prompt": user_message,
            "message": user_message,
            "text": user_message,
            "user_message": user_message,
            "source": "chat",
            "origin": "chat",
            "auto_approve": False,
            "auto_apply": False,
            "apply": False,
        }

        kwargs = {
            name: values[name]
            for name in parameters
            if name in values
        }

        required_positional = [
            parameter
            for parameter in parameters.values()
            if parameter.name != "self"
            and parameter.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and parameter.default is inspect.Parameter.empty
            and parameter.name not in kwargs
        ]

        if required_positional:
            # Most Buster runtime entry points accept one request/instruction.
            return func(user_message, **kwargs)

        if kwargs:
            return func(**kwargs)

        return func(user_message)

    def _run_repair_request(self, user_message: str) -> Any:
        """
        Send the request through the existing runtime-owned workflow.

        Runtime-level entry points are checked first. Direct service methods
        are compatibility fallbacks, but the service instance is still the
        singleton obtained from runtime_core.
        """
        runtime_methods = (
            "run_self_improvement",
            "run_repair",
            "request_repair",
            "submit_repair",
        )

        for name in runtime_methods:
            method = getattr(self.runtime_core, name, None)
            if callable(method):
                return self._invoke_with_supported_arguments(
                    method,
                    user_message,
                )

        service = self.repair_service

        service_methods = (
            "start_chat_repair",
            "start_repair",
            "request_repair",
            "submit",
            "run",
        )

        for name in service_methods:
            method = getattr(service, name, None)
            if callable(method):
                return self._invoke_with_supported_arguments(
                    method,
                    user_message,
                )

        raise RuntimeError(
            "The runtime-owned repair service has no supported repair "
            "entry point."
        )

    @staticmethod
    def _format_repair_result(result: Any) -> str:
        if result is None:
            return (
                "Repair request accepted by the runtime-owned workflow. "
                "Open Self Improvement or Mission Control to review progress."
            )

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            session_id = (
                result.get("session_id")
                or result.get("id")
                or result.get("repair_id")
            )
            status = result.get("status") or result.get("state")
            message = result.get("message") or result.get("summary")

            parts = ["Repair request routed through the unified runtime."]
            if session_id:
                parts.append(f"Session: {session_id}")
            if status:
                parts.append(f"Status: {status}")
            if message:
                parts.append(str(message))
            return "\n".join(parts)

        session_id = (
            getattr(result, "session_id", None)
            or getattr(result, "id", None)
        )
        status = (
            getattr(result, "status", None)
            or getattr(result, "state", None)
        )

        parts = ["Repair request routed through the unified runtime."]
        if session_id:
            parts.append(f"Session: {session_id}")
        if status:
            parts.append(f"Status: {status}")

        if len(parts) == 1:
            parts.append(str(result))

        return "\n".join(parts)

    def send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return

        self.input.clear()
        self.add_card(text, True)

        clean_text = text.lower().strip()

        try:
            if clean_text in CONVERSATIONAL_GREETINGS:
                self._set_state("speaking")
                reply = (
                    "Hello! I'm online and ready. "
                    "What are we building today?"
                )

            elif self._looks_like_repair_request(clean_text):
                self._set_state("thinking")
                result = self._run_repair_request(text)
                reply = self._format_repair_result(result)
                self._set_state("speaking")

            else:
                self._set_state("thinking")
                reply = self.live.brain(text)
                self._set_state("speaking")

        except Exception as exc:
            reply = f"Command failed: {exc}"
            self._set_state("error")

        self.add_card(reply, False)
        QTimer.singleShot(1200, lambda: self._set_state("idle"))

        if self.on_message:
            self.on_message()

    def clear(self) -> None:
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
