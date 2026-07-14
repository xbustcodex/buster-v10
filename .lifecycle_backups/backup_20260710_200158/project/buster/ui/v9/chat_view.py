from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame, QScrollArea

class ChatCard(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        top = QHBoxLayout()
        who = QLabel("👤  You" if is_user else "🤖  Buster")
        who.setStyleSheet("font-size:16px; font-weight:bold; color:#20a8ff;")
        time = QLabel(QTime.currentTime().toString("hh:mm:ss AP"))
        time.setObjectName("Small")
        top.addWidget(who)
        top.addStretch()
        top.addWidget(time)
        layout.addLayout(top)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet("font-size:14px; color:#dcecff;")
        layout.addWidget(body)

        if not is_user:
            actions = QHBoxLayout()
            for label in ["Copy", "Save", "Open Folder"]:
                actions.addWidget(QPushButton(label))
            actions.addStretch()
            layout.addLayout(actions)

class ChatView(QWidget):
    def __init__(self, live, on_message=None, on_state=None):
        super().__init__()
        self.live = live
        self.on_message = on_message
        self.on_state = on_state
        self.build()

    def build(self):
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
        self.input.setPlaceholderText("Type a command or message...")
        self.input.returnPressed.connect(self.send)
        send = QPushButton("Send")
        send.setMinimumWidth(110)
        send.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(send)
        layout.addLayout(row)

        self.add_card("workspace snapshot", True)
        self.add_card(self.live.safe(lambda: self.live.brain("workspace snapshot"), "Buster v9 ready."), False)

    def add_card(self, text, is_user=False):
        self.cards.insertWidget(self.cards.count() - 1, ChatCard(text, is_user))

    def send(self):
        text = self.input.text().strip()
        if not text:
            return

        self.input.clear()
        self.add_card(text, True)

        try:
            if self.on_state:
                self.on_state("thinking")
            reply = self.live.brain(text)
            if self.on_state:
                self.on_state("speaking")
        except Exception as exc:
            reply = f"Command failed: {exc}"
            if self.on_state:
                self.on_state("error")

        self.add_card(reply, False)
        if self.on_state:
            QTimer.singleShot(1200, lambda: self.on_state("idle"))

        if self.on_message:
            self.on_message()

    def clear(self):
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
