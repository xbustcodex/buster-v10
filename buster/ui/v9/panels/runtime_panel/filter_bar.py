from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class RuntimeFilterBar(QFrame):
    """
    Runtime Timeline toolbar.

    Emits UI signals only.
    Does not know anything about RuntimeDispatcher.
    """

    searchChanged = Signal(str)

    filterChanged = Signal(dict)

    pauseToggled = Signal(bool)

    clearRequested = Signal()

    exportRequested = Signal()

    DEFAULT_FILTERS = [
        "runtime",
        "vision",
        "voice",
        "agent",
        "job",
        "chat",
        "plugin",
        "face",
        "notification",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._paused = False
        self._checkboxes = {}

        self.setObjectName("RuntimeFilterBar")

        self.setStyleSheet("""
        QFrame#RuntimeFilterBar{
            background:#081321;
            border:1px solid #17385B;
            border-radius:10px;
        }

        QLabel{
            color:#DCEBFF;
            font-size:12px;
            font-weight:600;
        }

        QLineEdit{
            background:#06111E;
            color:white;
            border:1px solid #204E7A;
            border-radius:6px;
            padding:6px;
        }

        QPushButton{
            background:#0D2038;
            color:white;
            border:1px solid #245A8E;
            border-radius:6px;
            padding:6px 12px;
        }

        QPushButton:hover{
            background:#163251;
        }

        QCheckBox{
            color:#D5E5F8;
            spacing:5px;
        }
        """)

        self._build()

    # --------------------------------------------------

    def _build(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        #
        # search row
        #

        search_row = QHBoxLayout()

        lbl = QLabel("Search")

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Filter runtime events..."
        )

        self.search.textChanged.connect(
            self.searchChanged.emit
        )

        search_row.addWidget(lbl)
        search_row.addWidget(self.search)

        root.addLayout(search_row)

        #
        # filters
        #

        filter_row = QHBoxLayout()

        for name in self.DEFAULT_FILTERS:

            cb = QCheckBox(name.title())
            cb.setChecked(True)

            cb.toggled.connect(
                self._emit_filters
            )

            self._checkboxes[name] = cb

            filter_row.addWidget(cb)

        filter_row.addStretch()

        root.addLayout(filter_row)

        #
        # buttons
        #

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.pause_button = QPushButton("Pause")

        self.pause_button.clicked.connect(
            self.toggle_pause
        )

        self.clear_button = QPushButton("Clear")

        self.clear_button.clicked.connect(
            self.clearRequested.emit
        )

        self.export_button = QPushButton("Export")

        self.export_button.clicked.connect(
            self.exportRequested.emit
        )

        button_row.addWidget(self.pause_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.export_button)

        root.addLayout(button_row)

    # --------------------------------------------------

    def toggle_pause(self):

        self._paused = not self._paused

        self.pause_button.setText(
            "Resume"
            if self._paused
            else "Pause"
        )

        self.pauseToggled.emit(
            self._paused
        )

    # --------------------------------------------------

    def filters(self) -> dict:

        return {
            name: cb.isChecked()
            for name, cb in self._checkboxes.items()
        }

    # --------------------------------------------------

    def search_text(self) -> str:

        return self.search.text().strip()

    # --------------------------------------------------

    def set_search(self, text: str):

        self.search.setText(text)

    # --------------------------------------------------

    def clear_search(self):

        self.search.clear()

    # --------------------------------------------------

    def set_filter(
        self,
        name: str,
        enabled: bool,
    ):

        if name in self._checkboxes:
            self._checkboxes[name].setChecked(enabled)

    # --------------------------------------------------

    def enable_all(self):

        for cb in self._checkboxes.values():
            cb.setChecked(True)

    # --------------------------------------------------

    def disable_all(self):

        for cb in self._checkboxes.values():
            cb.setChecked(False)

    # --------------------------------------------------

    def paused(self) -> bool:

        return self._paused

    # --------------------------------------------------

    def _emit_filters(self):

        self.filterChanged.emit(
            self.filters()
        )