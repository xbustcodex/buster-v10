from __future__ import annotations

from typing import Optional, Any

try:
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QFrame,
        QGridLayout,
        QLabel,
    )
    from PySide6.QtCore import Signal, Qt, QTimer
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object

from buster.mission_control.snapshot import MissionControlSnapshot
from .health_card import HealthCard
from .metrics_card import MetricsCard
from .worker_leases_card import WorkerLeasesCard
from .circuit_breaker_card import CircuitBreakerCard
from .delegation_tree import DelegationTreeCard
from .learning_insights_card import LearningInsightsCard
from .dlq_card import DLQCard


class VitalSignsStrip(QFrame):
    """Top status strip displaying live system vital signs."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("VitalSignsStrip")
        self.setStyleSheet(
            """
            QFrame#VitalSignsStrip {
                background: #07111D;
                border: 1px solid #15324E;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QLabel {
                color: #8EA2C0;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)

        self.vitals_label = QLabel(
            "CPU <font color='#23B8FF'><b>12%</b></font> | "
            "RAM <font color='#23B8FF'><b>3.4 GB</b></font> | "
            "Tasks <font color='#23B8FF'><b>4</b></font> | "
            "Workers <font color='#23B8FF'><b>3/5</b></font> | "
            "Queue <font color='#23B8FF'><b>1</b></font> | "
            "DLQ <font color='#23B8FF'><b>0</b></font> | "
            "Events/s <font color='#23B8FF'><b>147</b></font> | "
            "AI Connected <font color='#31D158'>●</font>"
        )
        layout.addWidget(self.vitals_label)
        layout.addStretch()

    def update_vitals(
        self,
        cpu: str = "12%",
        ram: str = "3.4 GB",
        tasks: int = 4,
        workers: str = "3/5",
        queue: int = 1,
        dlq: int = 0,
        events_sec: int = 147,
        ai_online: bool = True,
    ) -> None:
        status_dot = "<font color='#31D158'>●</font>" if ai_online else "<font color='#FF4D4D'>●</font>"
        text = (
            f"CPU <font color='#23B8FF'><b>{cpu}</b></font> | "
            f"RAM <font color='#23B8FF'><b>{ram}</b></font> | "
            f"Tasks <font color='#23B8FF'><b>{tasks}</b></font> | "
            f"Workers <font color='#23B8FF'><b>{workers}</b></font> | "
            f"Queue <font color='#23B8FF'><b>{queue}</b></font> | "
            f"DLQ <font color='#23B8FF'><b>{dlq}</b></font> | "
            f"Events/s <font color='#23B8FF'><b>{events_sec}</b></font> | "
            f"AI Connected {status_dot}"
        )
        self.vitals_label.setText(text)


class MissionControlPanel(QWidget if PYSIDE6_AVAILABLE else object):
    """Composited PySide6 Development Mission Control Panel."""

    pause_delegation_requested = Signal() if PYSIDE6_AVAILABLE else None
    resume_delegation_requested = Signal() if PYSIDE6_AVAILABLE else None
    reset_circuit_requested = Signal(str) if PYSIDE6_AVAILABLE else None
    retry_dlq_requested = Signal(str) if PYSIDE6_AVAILABLE else None
    dismiss_dlq_requested = Signal(str) if PYSIDE6_AVAILABLE else None

    def __init__(
        self,
        live: Optional[Any] = None,
        runtime_core: Optional[Any] = None,
        parent: Optional[Any] = None,
    ):
        if not PYSIDE6_AVAILABLE:
            raise RuntimeError("PySide6 is required for MissionControlPanel")
        super().__init__(parent)

        if hasattr(live, "dispatcher") and not hasattr(runtime_core, "dispatcher"):
            self.runtime_core = live
            self.live = runtime_core
        else:
            self.runtime_core = runtime_core
            self.live = live

        self.setWindowTitle("BUSTER DEVELOPMENT MISSION CONTROL")
        self.resize(1100, 750)
        self._setup_ui()
        self._setup_polling()

    def _setup_ui(self) -> None:
        # Panel-wide Dark Theme Stylesheet for buttons & child frames
        self.setStyleSheet(
            """
            QWidget {
                background-color: #050B14;
                color: #EAF2FF;
                font-family: "Segoe UI", sans-serif;
            }

            QPushButton {
                background: #0A1D33;
                color: #DCEBFF;
                border: 1px solid #175A94;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
            }

            QPushButton:hover {
                background: #0E2A49;
                border-color: #23B8FF;
                color: #FFFFFF;
            }

            QPushButton:pressed {
                background: #071526;
            }

            QFrame {
                background: #07111D;
                border: 1px solid #15324E;
                border-radius: 8px;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. Header Controls Bar
        header_frame = QFrame()
        header_frame.setStyleSheet("background: transparent; border: none;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.pause_btn = QPushButton("Pause Delegation")
        self.pause_btn.clicked.connect(lambda: self.pause_delegation_requested.emit())
        
        self.resume_btn = QPushButton("Resume Delegation")
        self.resume_btn.clicked.connect(lambda: self.resume_delegation_requested.emit())

        # Manual Refresh Dashboard Button
        self.refresh_btn = QPushButton("🔄 Refresh Dashboard")
        self.refresh_btn.setStyleSheet(
            """
            QPushButton {
                background: #112A46;
                color: #23B8FF;
                border: 1px solid #23B8FF;
            }
            QPushButton:hover {
                background: #193E68;
                color: #FFFFFF;
            }
            """
        )
        self.refresh_btn.clicked.connect(self.manual_refresh)

        header_layout.addWidget(self.pause_btn)
        header_layout.addWidget(self.resume_btn)
        header_layout.addWidget(self.refresh_btn)
        header_layout.addStretch()

        main_layout.addWidget(header_frame)

        # 2. Vital Signs Strip
        self.vital_signs = VitalSignsStrip()
        main_layout.addWidget(self.vital_signs)

        # 3. Grid Layout for Cards
        grid = QGridLayout()
        grid.setSpacing(10)

        self.health_card = HealthCard()
        self.metrics_card = MetricsCard()
        self.worker_card = WorkerLeasesCard()
        self.circuit_card = CircuitBreakerCard()
        self.delegation_card = DelegationTreeCard()
        self.insights_card = LearningInsightsCard()
        self.dlq_card = DLQCard()

        # Connect sub-card signals to panel signals
        if PYSIDE6_AVAILABLE:
            if hasattr(self.circuit_card, "reset_requested"):
                self.circuit_card.reset_requested.connect(self.reset_circuit_requested.emit)
            if hasattr(self.dlq_card, "retry_requested"):
                self.dlq_card.retry_requested.connect(self.retry_dlq_requested.emit)
            if hasattr(self.dlq_card, "dismiss_requested"):
                self.dlq_card.dismiss_requested.connect(self.dismiss_dlq_requested.emit)

        # Row 0: Health, Metrics, Worker Leases
        grid.addWidget(self.health_card, 0, 0)
        grid.addWidget(self.metrics_card, 0, 1)
        grid.addWidget(self.worker_card, 0, 2)

        # Row 1: Circuits, Delegation Tree
        grid.addWidget(self.circuit_card, 1, 0, 1, 2)
        grid.addWidget(self.delegation_card, 1, 2)

        # Row 2: Learning Insights, DLQ
        grid.addWidget(self.insights_card, 2, 0, 1, 2)
        grid.addWidget(self.dlq_card, 2, 2)

        # Minimum heights prevent vertical squashing
        self.health_card.setMinimumHeight(110)
        self.metrics_card.setMinimumHeight(110)
        self.worker_card.setMinimumHeight(110)
        
        self.circuit_card.setMinimumHeight(180)
        self.delegation_card.setMinimumHeight(180)
        
        self.insights_card.setMinimumHeight(140)
        self.dlq_card.setMinimumHeight(140)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # Row 1 gets higher stretch factor so Circuits & Delegation Tree take priority space
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 1)

        main_layout.addLayout(grid, 1)

    def _setup_polling(self) -> None:
        """Polls runtime presenter if available."""
        if self.runtime_core and hasattr(self.runtime_core, "mission_control_presenter"):
            presenter = self.runtime_core.mission_control_presenter
            self._timer = QTimer(self)
            self._timer.timeout.connect(
                lambda: self.update_from_snapshot(presenter.create_snapshot())
            )
            self._timer.start(1000)

    def manual_refresh(self) -> None:
        """Triggers an immediate refresh across all cards and snapshots."""
        if self.runtime_core and hasattr(self.runtime_core, "mission_control_presenter"):
            presenter = self.runtime_core.mission_control_presenter
            self.update_from_snapshot(presenter.create_snapshot())
        
        # Directly trigger the learning insights card to re-read JSON on demand
        if hasattr(self.insights_card, "refresh_insights"):
            self.insights_card.refresh_insights()

    def update_from_snapshot(self, snapshot: MissionControlSnapshot) -> None:
        """Consumes an immutable snapshot and updates all child cards."""
        self.health_card.update_state(
            snapshot.health, snapshot.dlq_count, snapshot.failed_tasks
        )
        self.metrics_card.update_metrics(
            snapshot.completed_tasks, snapshot.failed_tasks, snapshot.metrics
        )
        self.worker_card.update_leases(snapshot.active_leases)
        self.circuit_card.update_circuits(snapshot.circuits)
        self.delegation_card.update_tree(snapshot.delegation_tree)
        self.insights_card.update_insights(snapshot.insights)
        self.dlq_card.update_dlq(snapshot.dlq_count)

        # Sync top status strip
        self.vital_signs.update_vitals(
            dlq=snapshot.dlq_count,
            tasks=snapshot.completed_tasks + snapshot.failed_tasks,
        )