from __future__ import annotations

from collections import deque
from typing import Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
)

from .filter_bar import RuntimeFilterBar
from .stats_bar import RuntimeStatsBar
from .event_card import RuntimeEventCard


class RuntimeTimelinePanel(QWidget):

    MAX_EVENTS = 500

    # Dispatcher callbacks may arrive from worker threads. This signal
    # queues the event back onto the Qt GUI thread before widgets are touched.
    runtime_event_received = Signal(dict)

    def __init__(
        self,
        runtime_core=None,
        parent=None,
    ):
        super().__init__(parent)

        self.runtime_core = runtime_core

        self.cards = deque()

        self.events = deque()

        self.paused = False

        self.pending_events = deque()

        self._dispatcher_connected = False

        self.setObjectName("RuntimeTimelinePanel")

        self.build_ui()

        self.connect_runtime()
        
        
    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12,12,12,12)

        layout.setSpacing(10)

        self.filter_bar = RuntimeFilterBar()

        self.stats_bar = RuntimeStatsBar()

        layout.addWidget(self.filter_bar)

        layout.addWidget(self.stats_bar)

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(True)

        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        layout.addWidget(self.scroll)

        self.container = QWidget()

        self.scroll.setWidget(self.container)

        self.timeline_layout = QVBoxLayout(
            self.container
        )

        self.timeline_layout.setAlignment(
            Qt.AlignTop
        )

        self.timeline_layout.setSpacing(8)

        self.timeline_layout.addStretch()
        
        

    def connect_runtime(self):

        # UI controls always connect, even when no runtime core is supplied.
        self.filter_bar.searchChanged.connect(
            self.apply_filters
        )

        self.filter_bar.filterChanged.connect(
            self.apply_filters
        )

        self.filter_bar.pauseToggled.connect(
            self.set_paused
        )

        self.filter_bar.clearRequested.connect(
            self.clear
        )

        self.filter_bar.exportRequested.connect(
            self.export_json
        )

        # A queued connection guarantees _process_runtime_event executes on
        # this widget's GUI thread.
        self.runtime_event_received.connect(
            self._process_runtime_event,
            Qt.ConnectionType.QueuedConnection,
        )

        if self.runtime_core is None:
            return

        self.runtime_core.dispatcher.subscribe(
            "*",
            self._handle_runtime_event,
        )

        self._dispatcher_connected = True
        
        
        
    def _handle_runtime_event(
        self,
        event: dict,
    ):
        """
        RuntimeDispatcher callback.

        This may be called from a worker thread, so it must not create or
        modify Qt widgets directly.
        """
        if isinstance(event, dict):
            self.runtime_event_received.emit(
                dict(event)
            )


    @Slot(dict)
    def _process_runtime_event(
        self,
        event: dict,
    ):
        """Process the event safely on the Qt GUI thread."""

        if self.paused:

            self.pending_events.append(
                event
            )

            return

        self.add_event(event)
        
        
        
    def add_event(
        self,
        event: dict,
    ):

        self.events.appendleft(event)

        card = RuntimeEventCard(
            event,
            parent=self.container,
        )

        self.cards.appendleft(card)

        self.timeline_layout.insertWidget(
            0,
            card,
        )

        while len(self.cards) > self.MAX_EVENTS:

            old = self.cards.pop()

            self.events.pop()

            old.deleteLater()

        self.refresh_stats()

        self.apply_filters()
        
        
    def refresh_stats(self):

        subscribers = 0

        dispatcher = "Unknown"

        if self.runtime_core:

            info = self.runtime_core.dispatcher.status()

            subscribers = sum(
                info.get(
                    "subscribers",
                    {},
                ).values()
            )

            dispatcher = "Healthy"

        self.stats_bar.update_stats({

            "events": len(self.events),

            "visible": sum(
                card.isVisible()
                for card in self.cards
            ),

            "filtered": len(self.events),

            "events_per_second": 0,

            "subscribers": subscribers,

            "dispatcher": dispatcher,

            "paused": self.paused,

        })
        
        
        
    def apply_filters(
        self,
        *_,
    ):

        search = self.filter_bar.search_text().lower()

        filters = self.filter_bar.filters()

        for card in self.cards:

            visible = True

            category = card.category

            if category in filters:

                visible &= filters[category]

            if search:

                visible &= (
                    search in card.event_type.lower()
                    or
                    search in str(card.payload).lower()
                )

            card.setVisible(visible)

        self.refresh_stats()
        
        
        
    def set_paused(
        self,
        paused: bool,
    ):

        self.paused = paused

        if not paused:

            while self.pending_events:

                self.add_event(

                    self.pending_events.popleft()

                )

        self.refresh_stats()
        
        
        
    def clear(self):

        while self.cards:

            self.cards.pop().deleteLater()

        self.events.clear()

        self.pending_events.clear()

        self.refresh_stats()
        
        
        
    def disconnect_runtime(self):

        if not self._dispatcher_connected:
            return

        if self.runtime_core is not None:

            try:

                self.runtime_core.dispatcher.unsubscribe(
                    "*",
                    self._handle_runtime_event,
                )

            except Exception:

                pass

        self._dispatcher_connected = False


    def closeEvent(self, event):

        self.disconnect_runtime()

        super().closeEvent(event)


    def export_json(self):

        print(

            "Export runtime timeline"

        )
        
        
        
    