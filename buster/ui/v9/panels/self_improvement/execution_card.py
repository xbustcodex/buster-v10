from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ExecutionCard(QFrame):
    """
    Live execution status card for Buster's Self Improvement workspace.

    The card is event-driven. It accepts runtime dispatcher events through
    ``handle_event`` and can also be updated directly with the public methods:

        start_execution(...)
        start_step(...)
        finish_step(...)
        finish_execution(...)
        fail_execution(...)
        reset()

    Supported event names
    ---------------------
    execution.started
    execution.step.started
    execution.step.finished
    execution.finished
    execution.failed
    execution.cancelled

    Signals
    -------
    execution_started(dict)
        Emitted when a new execution starts.

    execution_finished(dict)
        Emitted when an execution completes successfully.

    execution_failed(dict)
        Emitted when an execution fails.

    step_changed(dict)
        Emitted when the active execution step changes.
    """

    execution_started = Signal(dict)
    execution_finished = Signal(dict)
    execution_failed = Signal(dict)
    step_changed = Signal(dict)

    # Dispatcher callbacks may run on a worker thread. This signal safely
    # marshals all event handling back to the Qt GUI thread.
    runtime_event_received = Signal(object)

    VALID_STATES = {
        "idle",
        "running",
        "complete",
        "failed",
        "cancelled",
        "paused",
    }

    STATE_LABELS = {
        "idle": "Idle",
        "running": "Running",
        "complete": "Complete",
        "failed": "Failed",
        "cancelled": "Cancelled",
        "paused": "Paused",
    }

    def __init__(
        self,
        runtime_core=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self._subscribed_dispatcher = None
        self._display_kind = "execution"

        self._state = "idle"
        self._execution_id = ""
        self._job_name = "No active execution"
        self._agent = "—"
        self._step_name = "Waiting"
        self._completed_steps = 0
        self._total_steps = 0
        self._progress_value = 0
        self._started_at: Optional[datetime] = None

        self._elapsed_timer = QElapsedTimer()
        self._display_timer = QTimer(self)
        self._display_timer.setInterval(1000)
        self._display_timer.timeout.connect(
            self._update_elapsed_display
        )

        self.setObjectName("SelfImprovementExecutionCard")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._build_ui()
        self._apply_styles()

        self.runtime_event_received.connect(
            self._process_runtime_event,
            Qt.ConnectionType.QueuedConnection,
        )

        self._subscribe_to_runtime()
        self.refresh_from_runtime_status()
        self._refresh_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self.title_label = QLabel("Execution", self)
        self.title_label.setObjectName("ExecutionCardTitle")

        self.state_indicator = QLabel("●", self)
        self.state_indicator.setObjectName("ExecutionStateIndicator")
        self.state_indicator.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.state_indicator.setFixedWidth(14)

        self.state_label = QLabel("Idle", self)
        self.state_label.setObjectName("ExecutionStateLabel")

        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.state_indicator)
        header.addWidget(self.state_label)

        root.addLayout(header)

        self.job_label = QLabel(
            "No active execution",
            self,
        )
        self.job_label.setObjectName("ExecutionJobName")
        self.job_label.setWordWrap(True)
        root.addWidget(self.job_label)

        details = QGridLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setHorizontalSpacing(16)
        details.setVerticalSpacing(7)

        details.addWidget(
            self._make_caption("Current step"),
            0,
            0,
        )
        self.step_value = self._make_value("Waiting")
        details.addWidget(self.step_value, 0, 1)

        details.addWidget(
            self._make_caption("Current agent"),
            1,
            0,
        )
        self.agent_value = self._make_value("—")
        details.addWidget(self.agent_value, 1, 1)

        details.addWidget(
            self._make_caption("Progress"),
            2,
            0,
        )
        self.progress_text = self._make_value("0 / 0")
        details.addWidget(self.progress_text, 2, 1)

        details.addWidget(
            self._make_caption("Elapsed"),
            3,
            0,
        )
        self.elapsed_value = self._make_value("00:00:00")
        details.addWidget(self.elapsed_value, 3, 1)

        details.setColumnStretch(1, 1)
        root.addLayout(details)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("ExecutionProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        root.addWidget(self.progress_bar)

        self.message_label = QLabel(
            "Waiting for an execution job.",
            self,
        )
        self.message_label.setObjectName("ExecutionMessage")
        self.message_label.setWordWrap(True)
        root.addWidget(self.message_label)

    def _make_caption(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("ExecutionCaption")
        return label

    def _make_value(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("ExecutionValue")
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        return label

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementExecutionCard {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QLabel#ExecutionCardTitle {
                color: #f2f5f8;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#ExecutionStateIndicator {
                color: #64748b;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#ExecutionStateLabel {
                color: #aeb8c3;
                font-size: 11px;
                font-weight: 700;
            }

            QLabel#ExecutionJobName {
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#ExecutionCaption {
                color: #7f8b99;
                font-size: 10px;
                font-weight: 600;
            }

            QLabel#ExecutionValue {
                color: #dbe3eb;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel#ExecutionMessage {
                color: #8f9baa;
                font-size: 10px;
            }

            QProgressBar#ExecutionProgressBar {
                background-color: #202833;
                border: none;
                border-radius: 4px;
            }

            QProgressBar#ExecutionProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 4px;
            }
            """
        )

    def _subscribe_to_runtime(self) -> None:
        """Subscribe once to execution and self-improvement events."""
        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        subscribe = getattr(dispatcher, "subscribe", None)

        if not callable(subscribe):
            return

        if dispatcher is self._subscribed_dispatcher:
            return

        for pattern in (
            "execution.*",
            "self_improvement.execution.*",
            "self_improvement.cycle.finished",
        ):
            try:
                subscribe(pattern, self.handle_event)
            except Exception:
                continue

        self._subscribed_dispatcher = dispatcher

    def set_runtime_core(self, runtime_core) -> None:
        self.runtime_core = runtime_core
        self._subscribed_dispatcher = None
        self._subscribe_to_runtime()
        self.refresh_from_runtime_status()

    @Slot(object)
    def handle_event(self, event: Any) -> None:
        """Thread-safe dispatcher callback."""
        self.runtime_event_received.emit(event)

    @Slot(object)
    def _process_runtime_event(self, event: Any) -> None:
        """Handle dispatcher events on the Qt GUI thread."""
        event_name, payload = self._normalize_event(event)

        if not event_name:
            return

        if event_name == "self_improvement.cycle.finished":
            self.show_scan_result(payload)
            return

        if event_name.endswith("execution.started"):
            self.start_execution(
                execution_id=self._text(
                    payload,
                    "execution_id",
                    "job_id",
                    "id",
                ),
                job_name=self._text(
                    payload,
                    "job_name",
                    "title",
                    "job",
                    default="Execution job",
                ),
                agent=self._text(
                    payload,
                    "agent",
                    "agent_name",
                    default="—",
                ),
                total_steps=self._integer(
                    payload,
                    "total_steps",
                    "steps_total",
                    default=0,
                ),
                message=self._text(
                    payload,
                    "message",
                    default="Execution started.",
                ),
                metadata=payload,
            )
            return

        if event_name.endswith("execution.step.started"):
            self.start_step(
                step_name=self._text(
                    payload,
                    "step_name",
                    "step",
                    "name",
                    default="Running step",
                ),
                agent=self._text(
                    payload,
                    "agent",
                    "agent_name",
                    default=self._agent,
                ),
                step_index=self._integer(
                    payload,
                    "step_index",
                    "current_step",
                    "index",
                    default=self._completed_steps + 1,
                ),
                total_steps=self._integer(
                    payload,
                    "total_steps",
                    "steps_total",
                    default=self._total_steps,
                ),
                message=self._text(
                    payload,
                    "message",
                    default="Step in progress.",
                ),
                metadata=payload,
            )
            return

        if event_name.endswith("execution.step.finished"):
            self.finish_step(
                step_name=self._text(
                    payload,
                    "step_name",
                    "step",
                    "name",
                    default=self._step_name,
                ),
                completed_steps=self._integer(
                    payload,
                    "completed_steps",
                    "step_index",
                    "current_step",
                    default=self._completed_steps + 1,
                ),
                total_steps=self._integer(
                    payload,
                    "total_steps",
                    "steps_total",
                    default=self._total_steps,
                ),
                message=self._text(
                    payload,
                    "message",
                    default="Step complete.",
                ),
                metadata=payload,
            )
            return

        if event_name.endswith("execution.finished"):
            self.finish_execution(
                message=self._text(
                    payload,
                    "message",
                    default="Execution completed successfully.",
                ),
                metadata=payload,
            )
            return

        if event_name.endswith("execution.failed"):
            self.fail_execution(
                error=self._text(
                    payload,
                    "error",
                    "message",
                    default="Execution failed.",
                ),
                metadata=payload,
            )
            return

        if event_name.endswith("execution.cancelled"):
            self.cancel_execution(
                message=self._text(
                    payload,
                    "message",
                    default="Execution cancelled.",
                ),
                metadata=payload,
            )

    def start_scan(self, mode: str = "manual") -> None:
        """Display live scan activity, including in Manual mode."""
        self._display_kind = "scan"
        self.title_label.setText("Scan Status")
        self._state = "running"
        self._execution_id = ""
        self._job_name = f"Self Improvement Scan · {str(mode).title()}"
        self._agent = "Scanner"
        self._step_name = "Scanning project"
        self._completed_steps = 0
        self._total_steps = 5
        self._progress_value = 5
        self._started_at = datetime.now()

        self._elapsed_timer.restart()
        self._display_timer.start()
        self.message_label.setText(
            "Checking syntax, TODO comments, architecture, tests and Git safety."
        )
        self._refresh_ui()

    def show_scan_result(self, result: Any) -> None:
        """Display a completed scan result or saved last-cycle result."""
        if hasattr(result, "to_dict") and callable(result.to_dict):
            try:
                result = result.to_dict()
            except Exception:
                return

        if not isinstance(result, Mapping):
            return

        findings = result.get("findings", [])
        if not isinstance(findings, list):
            findings = []

        mode = str(result.get("mode", "manual")).title()
        status = str(result.get("status", "complete"))
        message = str(result.get("message", "")).strip()

        category_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}

        for finding in findings:
            if not isinstance(finding, Mapping):
                continue
            category = str(finding.get("category", "other")).lower()
            severity = str(finding.get("severity", "info")).lower()
            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        summary_parts = []
        for category in ("syntax", "tests", "safety", "architecture", "todo"):
            count = category_counts.get(category, 0)
            if count:
                summary_parts.append(f"{category.title()}: {count}")

        self._display_kind = "scan"
        self.title_label.setText("Scan Status")
        self._state = "complete" if status not in {"failed", "error"} else "failed"
        self._job_name = f"Self Improvement Scan · {mode}"
        self._agent = "Scanner"
        self._step_name = "Scan completed" if self._state == "complete" else "Scan failed"
        self._completed_steps = 5
        self._total_steps = 5
        self._progress_value = 100 if self._state == "complete" else 0
        self._display_timer.stop()

        detail = " · ".join(summary_parts) if summary_parts else "No actionable findings"
        self.message_label.setText(
            f"{len(findings)} finding(s). {detail}"
            + (f" — {message}" if message else "")
        )

        self._refresh_ui()
        self._update_elapsed_display()

    def fail_scan(self, error: str) -> None:
        self._display_kind = "scan"
        self.title_label.setText("Scan Status")
        self._state = "failed"
        self._job_name = "Self Improvement Scan"
        self._agent = "Scanner"
        self._step_name = "Scan failed"
        self._display_timer.stop()
        self.message_label.setText(error or "The scan failed.")
        self._refresh_ui()
        self._update_elapsed_display()

    def refresh_from_runtime_status(self) -> None:
        """Restore the most recent scan when the workspace opens."""
        runtime = self.runtime_core
        if runtime is None:
            return

        helper = getattr(runtime, "self_improvement_status", None)
        status = None

        if callable(helper):
            try:
                status = helper()
            except Exception:
                status = None

        if not isinstance(status, Mapping):
            service = getattr(runtime, "self_improvement", None)
            getter = getattr(service, "status", None)
            if callable(getter):
                try:
                    status = getter()
                except Exception:
                    status = None

        if not isinstance(status, Mapping):
            return

        last_cycle = status.get("last_cycle")
        if isinstance(last_cycle, Mapping):
            self.show_scan_result(last_cycle)

    def start_execution(
        self,
        *,
        execution_id: str = "",
        job_name: str = "Execution job",
        agent: str = "—",
        total_steps: int = 0,
        message: str = "Execution started.",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._display_kind = "execution"
        self.title_label.setText("Execution")
        self._state = "running"
        self._execution_id = execution_id
        self._job_name = job_name or "Execution job"
        self._agent = agent or "—"
        self._step_name = "Starting"
        self._completed_steps = 0
        self._total_steps = max(0, int(total_steps))
        self._progress_value = 0
        self._started_at = datetime.now()

        self._elapsed_timer.restart()
        self._display_timer.start()

        self.message_label.setText(message)
        self._refresh_ui()
        self.execution_started.emit(
            dict(metadata or {})
        )

    def start_step(
        self,
        *,
        step_name: str,
        agent: str = "—",
        step_index: Optional[int] = None,
        total_steps: Optional[int] = None,
        message: str = "Step in progress.",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if self._state != "running":
            self._state = "running"
            if not self._elapsed_timer.isValid():
                self._elapsed_timer.start()
            self._display_timer.start()

        self._step_name = step_name or "Running step"
        self._agent = agent or self._agent

        if total_steps is not None:
            self._total_steps = max(
                0,
                int(total_steps),
            )

        if step_index is not None:
            current_index = max(
                0,
                int(step_index) - 1,
            )
            self._completed_steps = min(
                current_index,
                self._total_steps
                if self._total_steps
                else current_index,
            )

        self.message_label.setText(message)
        self._calculate_progress()
        self._refresh_ui()
        self.step_changed.emit(
            dict(metadata or {})
        )

    def finish_step(
        self,
        *,
        step_name: Optional[str] = None,
        completed_steps: Optional[int] = None,
        total_steps: Optional[int] = None,
        message: str = "Step complete.",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if step_name:
            self._step_name = step_name

        if total_steps is not None:
            self._total_steps = max(
                0,
                int(total_steps),
            )

        if completed_steps is None:
            self._completed_steps += 1
        else:
            self._completed_steps = max(
                0,
                int(completed_steps),
            )

        if self._total_steps:
            self._completed_steps = min(
                self._completed_steps,
                self._total_steps,
            )

        self.message_label.setText(message)
        self._calculate_progress()
        self._refresh_ui()
        self.step_changed.emit(
            dict(metadata or {})
        )

    def finish_execution(
        self,
        *,
        message: str = "Execution completed successfully.",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._state = "complete"
        self._display_timer.stop()

        if self._total_steps:
            self._completed_steps = self._total_steps

        self._progress_value = 100
        self._step_name = "Complete"
        self.message_label.setText(message)
        self._refresh_ui()
        self._update_elapsed_display()
        self.execution_finished.emit(
            dict(metadata or {})
        )

    def fail_execution(
        self,
        *,
        error: str = "Execution failed.",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._state = "failed"
        self._display_timer.stop()
        self._step_name = "Failed"
        self.message_label.setText(error)
        self._refresh_ui()
        self._update_elapsed_display()
        self.execution_failed.emit(
            dict(metadata or {})
        )

    def cancel_execution(
        self,
        *,
        message: str = "Execution cancelled.",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._state = "cancelled"
        self._display_timer.stop()
        self._step_name = "Cancelled"
        self.message_label.setText(message)
        self._refresh_ui()
        self._update_elapsed_display()
        self.execution_failed.emit(
            dict(metadata or {})
        )

    def pause_execution(
        self,
        message: str = "Execution paused.",
    ) -> None:
        if self._state != "running":
            return
        self._state = "paused"
        self._display_timer.stop()
        self.message_label.setText(message)
        self._refresh_ui()

    def resume_execution(
        self,
        message: str = "Execution resumed.",
    ) -> None:
        if self._state != "paused":
            return
        self._state = "running"
        self._display_timer.start()
        self.message_label.setText(message)
        self._refresh_ui()

    def reset(self) -> None:
        self._display_kind = "execution"
        self.title_label.setText("Execution")
        self._display_timer.stop()
        self._elapsed_timer.invalidate()

        self._state = "idle"
        self._execution_id = ""
        self._job_name = "No active execution"
        self._agent = "—"
        self._step_name = "Waiting"
        self._completed_steps = 0
        self._total_steps = 0
        self._progress_value = 0
        self._started_at = None

        self.message_label.setText(
            "Waiting for an execution job."
        )
        self.elapsed_value.setText("00:00:00")
        self._refresh_ui()

    def set_progress(
        self,
        completed: int,
        total: int,
    ) -> None:
        self._completed_steps = max(
            0,
            int(completed),
        )
        self._total_steps = max(
            0,
            int(total),
        )

        if self._total_steps:
            self._completed_steps = min(
                self._completed_steps,
                self._total_steps,
            )

        self._calculate_progress()
        self._refresh_ui()

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "execution_id": self._execution_id,
            "job_name": self._job_name,
            "agent": self._agent,
            "step_name": self._step_name,
            "completed_steps": self._completed_steps,
            "total_steps": self._total_steps,
            "progress": self._progress_value,
            "elapsed": self.elapsed_value.text(),
            "started_at": (
                self._started_at.isoformat()
                if self._started_at
                else None
            ),
        }

    def _calculate_progress(self) -> None:
        if self._total_steps <= 0:
            self._progress_value = 0
            return

        self._progress_value = max(
            0,
            min(
                100,
                round(
                    (
                        self._completed_steps
                        / self._total_steps
                    )
                    * 100
                ),
            ),
        )

    def _refresh_ui(self) -> None:
        self.state_label.setText(
            self.STATE_LABELS.get(
                self._state,
                self._state.title(),
            )
        )
        self.job_label.setText(self._job_name)
        self.step_value.setText(self._step_name)
        self.agent_value.setText(self._agent)

        if self._total_steps:
            progress_text = (
                f"{self._completed_steps} / "
                f"{self._total_steps}"
            )
        else:
            progress_text = (
                f"{self._progress_value}%"
                if self._state == "running"
                else "0 / 0"
            )

        self.progress_text.setText(progress_text)
        self.progress_bar.setValue(
            self._progress_value
        )
        self._apply_state_appearance()

    def _apply_state_appearance(self) -> None:
        indicator_colors = {
            "idle": "#64748b",
            "running": "#38bdf8",
            "complete": "#22c55e",
            "failed": "#ef4444",
            "cancelled": "#f59e0b",
            "paused": "#f59e0b",
        }

        progress_colors = {
            "idle": "#64748b",
            "running": "#3b82f6",
            "complete": "#22c55e",
            "failed": "#ef4444",
            "cancelled": "#f59e0b",
            "paused": "#f59e0b",
        }

        indicator = indicator_colors.get(
            self._state,
            "#64748b",
        )
        progress = progress_colors.get(
            self._state,
            "#3b82f6",
        )

        self.state_indicator.setStyleSheet(
            f"color: {indicator};"
        )

        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #202833;
                border: none;
                border-radius: 4px;
            }}

            QProgressBar::chunk {{
                background-color: {progress};
                border-radius: 4px;
            }}
            """
        )

    def _update_elapsed_display(self) -> None:
        if not self._elapsed_timer.isValid():
            self.elapsed_value.setText("00:00:00")
            return

        elapsed_seconds = max(
            0,
            self._elapsed_timer.elapsed() // 1000,
        )

        hours, remainder = divmod(
            elapsed_seconds,
            3600,
        )
        minutes, seconds = divmod(
            remainder,
            60,
        )

        self.elapsed_value.setText(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )

    @staticmethod
    def _normalize_event(
        event: Any,
    ) -> tuple[str, dict[str, Any]]:
        if isinstance(event, Mapping):
            event_name = str(
                event.get(
                    "event",
                    event.get(
                        "type",
                        event.get(
                            "name",
                            "",
                        ),
                    ),
                )
            )

            payload = event.get(
                "payload",
                event.get(
                    "data",
                    event,
                ),
            )

            return (
                event_name,
                dict(payload)
                if isinstance(payload, Mapping)
                else {},
            )

        event_name = str(
            getattr(
                event,
                "event",
                getattr(
                    event,
                    "type",
                    getattr(
                        event,
                        "name",
                        "",
                    ),
                ),
            )
        )

        payload = getattr(
            event,
            "payload",
            getattr(
                event,
                "data",
                {},
            ),
        )

        return (
            event_name,
            dict(payload)
            if isinstance(payload, Mapping)
            else {},
        )

    @staticmethod
    def _text(
        payload: Mapping[str, Any],
        *keys: str,
        default: str = "",
    ) -> str:
        for key in keys:
            value = payload.get(key)
            if value is not None and value != "":
                return str(value)
        return default

    @staticmethod
    def _integer(
        payload: Mapping[str, Any],
        *keys: str,
        default: int = 0,
    ) -> int:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return default
