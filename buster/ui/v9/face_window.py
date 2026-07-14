from __future__ import annotations

from datetime import datetime


from PySide6.QtCore import QTimer, Qt, Slot, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from buster.ui.v9.widgets.animated_avatar import AnimatedAvatar


class StatusRow(QFrame):
    def __init__(self, name: str, value: str = "Unknown", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color:#CFD9E8;font-size:13px;")
        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.value_label)
        self.set_value(value, "muted")

    def set_value(self, value: str, level: str = "ok") -> None:
        colors = {"ok":"#24D66A", "info":"#23B8FF", "warning":"#FFB020", "error":"#FF5C5C", "muted":"#8393A8"}
        self.value_label.setText(value)
        self.value_label.setStyleSheet(f"color:{colors.get(level, colors['info'])};font-size:13px;font-weight:600;")


class FaceWindow(QWidget):
    runtime_event_signal = Signal(dict)
    def __init__(self, runtime_core=None, parent=None):
        super().__init__(parent)
        self.runtime_core = runtime_core
        self.manual_state = False
        self.current_state = "idle"
        self._dispatcher_subscriptions = []
        self.runtime_event_signal.connect(self._handle_runtime_event)

        self.setWindowTitle("Buster Face — Enhanced")
        self.resize(1180, 820)
        self.setMinimumSize(920, 680)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setStyleSheet("""
            QWidget { background:#050B14;color:#EAF2FF;font-family:'Segoe UI'; }
            QFrame#Panel { background:#081321;border:1px solid #163558;border-radius:16px; }
            QFrame#AvatarCard { background:#06101D;border:1px solid #0D3764;border-radius:20px; }
            QPushButton { background:#0A1D33;color:#DCEBFF;border:1px solid #175A94;border-radius:10px;padding:9px 12px;font-weight:600; }
            QPushButton:hover { background:#0E2A49;border-color:#23B8FF; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        self._build_header(root)
        self._build_body(root)
        self._build_message(root)
        self._build_footer(root)
        
        self.runtime_event_signal.connect(
            self._handle_runtime_event
        )

        self._connect_runtime_dispatcher()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_runtime)
        
        self.timer.start(5000)
        
        self.refresh_runtime()

    def _panel(self):
        panel = QFrame(); panel.setObjectName("Panel"); return panel

    def _build_header(self, root):
        panel = self._panel(); layout = QHBoxLayout(panel)
        title = QLabel("BUSTER")
        title.setStyleSheet("font-size:34px;font-weight:800;color:#23B8FF;letter-spacing:3px;")
        subtitle = QLabel("AI DEVELOPMENT COMPANION")
        subtitle.setStyleSheet("font-size:12px;color:#7894B5;letter-spacing:2px;")
        brand = QVBoxLayout(); brand.addWidget(title); brand.addWidget(subtitle)
        self.state_chip = QLabel("● Idle")
        self.state_chip.setMinimumWidth(180); self.state_chip.setAlignment(Qt.AlignCenter)
        self.state_chip.setStyleSheet("background:#092238;color:#23B8FF;border:1px solid #165F9E;border-radius:14px;padding:10px;font-size:16px;font-weight:700;")
        layout.addLayout(brand); layout.addStretch(); layout.addWidget(self.state_chip)
        root.addWidget(panel)

    def _build_body(self, root):
        body = QHBoxLayout(); body.setSpacing(12)
        left = self._panel(); left.setFixedWidth(320)
        layout = QVBoxLayout(left); layout.setContentsMargins(16,16,16,16)
        heading = QLabel("CURRENT STATE"); heading.setStyleSheet("color:#7894B5;font-size:12px;font-weight:700;")
        self.state_label = QLabel("Idle"); self.state_label.setStyleSheet("font-size:24px;font-weight:700;color:#23B8FF;")
        self.detail_label = QLabel("Buster is ready."); self.detail_label.setWordWrap(True); self.detail_label.setStyleSheet("font-size:13px;color:#9FB8D5;")
        layout.addWidget(heading); layout.addWidget(self.state_label); layout.addWidget(self.detail_label)
        status_heading = QLabel("SYSTEM STATUS"); status_heading.setStyleSheet("color:#7894B5;font-size:12px;font-weight:700;margin-top:8px;")
        layout.addWidget(status_heading)
        self.rows = {name: StatusRow(label) for name, label in {
            "runtime":"Runtime", "mission":"Mission Control", "agents":"Agents",
            "jobs":"Jobs", "memory":"Memory", "voice":"Voice", "vision":"Vision",
        }.items()}
        for row in self.rows.values(): layout.addWidget(row)
        mood = QLabel("MOOD"); mood.setStyleSheet("color:#7894B5;font-size:12px;font-weight:700;margin-top:8px;")
        layout.addWidget(mood)
        grid = QGridLayout()
        for i, (title, state) in enumerate([
            ("Idle","idle"),("Think","thinking"),("Work","working"),("Listen","listening"),
            ("Speak","speaking"),("Success","success"),("Warn","warning"),("Error","error"),
        ]):
            btn = QPushButton(title); btn.clicked.connect(lambda _, s=state: self.set_state(s, manual=True)); grid.addWidget(btn, i//2, i%2)
        layout.addLayout(grid)
        auto = QPushButton("Return to Auto Runtime State"); auto.clicked.connect(self.enable_auto_state); layout.addWidget(auto); layout.addStretch()

        avatar_panel = self._panel(); avatar_layout = QVBoxLayout(avatar_panel)
        self.avatar = AnimatedAvatar("idle", avatar_panel); avatar_layout.addWidget(self.avatar, 1)
        body.addWidget(left); body.addWidget(avatar_panel, 1); root.addLayout(body, 1)

    def _build_message(self, root):
        panel = self._panel(); layout = QHBoxLayout(panel)
        icon = QLabel("•••"); icon.setFixedSize(54,54); icon.setAlignment(Qt.AlignCenter); icon.setStyleSheet("background:#0A3155;color:#23B8FF;border:1px solid #1677C5;border-radius:27px;font-size:20px;font-weight:800;")
        text = QVBoxLayout(); self.message_title = QLabel("Ready"); self.message_title.setStyleSheet("font-size:17px;font-weight:700;")
        self.message_detail = QLabel("Buster is standing by."); self.message_detail.setWordWrap(True); self.message_detail.setStyleSheet("font-size:14px;color:#9FB8D5;")
        text.addWidget(self.message_title); text.addWidget(self.message_detail)
        wave = QLabel("▁▂▃▅▇▆▃▂▁  ▁▃▆▇▅▃▂"); wave.setStyleSheet("font-family:Consolas;font-size:22px;color:#167DFF;")
        layout.addWidget(icon); layout.addLayout(text, 1); layout.addWidget(wave); root.addWidget(panel)

    def _build_footer(self, root):
        layout = QHBoxLayout()
        self.ready = QLabel("● Ready"); self.ready.setStyleSheet("color:#24D66A;font-size:14px;font-weight:600;")
        version = QLabel("Buster OS v10.7"); version.setStyleSheet("color:#23B8FF;font-size:14px;font-weight:600;")
        self.clock = QLabel(); self.clock.setStyleSheet("color:#9FB8D5;font-size:14px;")
        layout.addWidget(self.ready); layout.addStretch(); layout.addWidget(version); layout.addStretch(); layout.addWidget(self.clock); root.addLayout(layout)

    def set_state(self, state: str, detail: str | None = None, manual: bool = False):
        self.manual_state = manual
        self.current_state = str(state or "idle").lower()
        defaults = {
            "idle":"Buster is ready.", "thinking":"Analyzing your request and planning the next action.",
            "speaking":"Buster is responding.", "working":"Runtime agents are processing the current task.",
            "listening":"Listening for a voice command.", "success":"The operation completed successfully.",
            "warning":"Something needs your attention.", "error":"An operation failed. Check Mission Control.",
            "sleeping":"Runtime activity is currently idle.", "confused":"More information may be needed.",
            "excited":"A major milestone was reached.",
        }
        detail = detail or defaults.get(self.current_state, "Buster is active.")
        title = self.current_state.title()
        self.avatar.set_state(self.current_state, detail)
        self.state_label.setText(title); self.detail_label.setText(detail)
        self.message_title.setText(title); self.message_detail.setText(detail)
        self.state_chip.setText(f"● {title}")

    def enable_auto_state(self):
        self.manual_state = False
        self.refresh_runtime()

    def refresh_runtime(self):
        self.clock.setText(datetime.now().strftime("%I:%M:%S %p"))
        if not self.runtime_core:
            self.rows["runtime"].set_value("Not Connected", "error")
            if not self.manual_state: self.set_state("warning", "Runtime core is not connected.")
            return
        try:
            status = self.runtime_core.status(); jobs = self.runtime_core.jobs.status(); agents = self.runtime_core.agents.status(); memory = self.runtime_core.agent_memory.status(); events = self.runtime_core.events.recent(10)
            counts = jobs.get("counts", {})
            running, pending, failed, completed = [int(counts.get(k, 0)) for k in ("running","pending","failed","completed")]
            started = bool(status.get("started")); agent_count = int(agents.get("count", 0))
            self.rows["runtime"].set_value("Connected" if started else "Ready", "ok" if started else "info")
            self.rows["mission"].set_value("Active", "info")
            self.rows["agents"].set_value(f"{agent_count} Online", "ok")
            self.rows["jobs"].set_value(f"{running} Running" if running else f"{completed} Complete", "warning" if running else "ok")
            self.rows["memory"].set_value("Healthy" if memory is not None else "Unknown", "ok" if memory is not None else "warning")
            self.rows["voice"].set_value("Ready", "info"); self.rows["vision"].set_value("Ready", "info")
            if not self.manual_state:
                if failed: self.set_state("error", f"{failed} runtime job failed.")
                elif running: self.set_state("working", f"{running} runtime job is currently running.")
                elif pending: self.set_state("thinking", f"{pending} runtime job is waiting.")
                elif events and str(events[-1].get("type", "")).endswith("finished"): self.set_state("success", "The latest runtime operation completed.")
                elif started: self.set_state("idle", "Runtime connected and ready.")
                else: self.set_state("sleeping", "Runtime is not currently active.")
        except Exception as exc:
            self.rows["runtime"].set_value("Unavailable", "error")
            if not self.manual_state: self.set_state("warning", f"Runtime status unavailable: {exc}")

    def closeEvent(self, event):
        self.hide(); event.ignore()
        
    def shutdown(self) -> None:
        self._disconnect_runtime_dispatcher()

        if self.timer.isActive():
            self.timer.stop()

        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.close()    
        
    def _connect_runtime_dispatcher(self) -> None:
        if not self.runtime_core:
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )

        if dispatcher is None:
            return

        event_types = [
            "runtime.*",
            "job.*",
            "agent.*",
            "voice.*",
            "vision.*",
            "face.state",
            "notification",
        ]

        for event_type in event_types:
            dispatcher.subscribe(
                event_type,
                self._receive_runtime_event,
            )

            self._dispatcher_subscriptions.append(
                event_type
            )


    def _disconnect_runtime_dispatcher(self) -> None:
        if not self.runtime_core:
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )

        if dispatcher is None:
            return

        for event_type in self._dispatcher_subscriptions:
            dispatcher.unsubscribe(
                event_type,
                self._receive_runtime_event,
            )

        self._dispatcher_subscriptions.clear()


    def _receive_runtime_event(self, event: dict) -> None:
        """
        May be called from a runtime or worker thread.
        Forward the event safely to Qt's GUI thread.
        """
        self.runtime_event_signal.emit(event)    
        
    @Slot(dict)
    def _handle_runtime_event(self, event: dict) -> None:
        event_type = str(
            event.get("type", "")
        )

        payload = event.get("payload", {})

        if not isinstance(payload, dict):
            payload = {}

        if event_type in {
            "runtime.started",
            "runtime.core.started",
        }:
            self.set_state(
                "success",
                "Buster runtime connected.",
            )

        elif event_type in {
            "runtime.stopped",
            "runtime.core.stopped",
        }:
            self.set_state(
                "sleeping",
                "Buster runtime stopped.",
            )

        elif event_type == "runtime.request":
            request = payload.get(
                "request",
                "Processing your request.",
            )

            self.set_state(
                "thinking",
                str(request),
            )

        elif event_type == "job.created":
            title = (
                payload.get("title")
                or payload.get("name")
                or payload.get("job_type")
                or "Runtime job"
            )

            self.set_state(
                "thinking",
                f"Preparing: {title}",
            )

        elif event_type == "job.started":
            title = (
                payload.get("title")
                or payload.get("job")
                or payload.get("job_id")
                or "Runtime job"
            )

            self.set_state(
                "working",
                f"Running: {title}",
            )

        elif event_type == "job.progress":
            title = (
                payload.get("title")
                or payload.get("job")
                or "Runtime job"
            )

            progress = payload.get("progress")

            if progress is None:
                message = f"Working on: {title}"
            else:
                message = (
                    f"{title}: {progress}% complete"
                )

            self.set_state(
                "working",
                message,
            )

        elif event_type == "job.finished":
            self.set_state(
                "success",
                "Runtime job completed successfully.",
            )

            QTimer.singleShot(
                2500,
                self._return_to_runtime_state,
            )

        elif event_type == "job.failed":
            error = payload.get(
                "error",
                "A runtime job failed.",
            )

            self.set_state(
                "error",
                str(error),
            )

        elif event_type == "agent.started":
            agent = str(
                payload.get("agent", "Agent")
            )

            state = (
                "thinking"
                if agent.lower() == "planner"
                else "working"
            )

            self.set_state(
                state,
                f"{agent.title()} Agent is running.",
            )

        elif event_type == "agent.finished":
            agent = str(
                payload.get("agent", "Agent")
            )

            self.set_state(
                "success",
                f"{agent.title()} Agent completed.",
            )

            QTimer.singleShot(
                2000,
                self._return_to_runtime_state,
            )

        elif event_type == "agent.failed":
            agent = str(
                payload.get("agent", "Agent")
            )

            error = payload.get(
                "error",
                "Agent execution failed.",
            )

            self.set_state(
                "error",
                f"{agent.title()}: {error}",
            )

        elif event_type == "voice.status":
            self._handle_voice_event(payload)

        elif event_type == "voice.transcribed":
            text = str(
                payload.get("text", "")
            )

            self.set_state(
                "success",
                f'Heard: "{text[:120]}"',
            )

        elif event_type == "vision.status":
            self._handle_vision_event(payload)

        elif event_type == "vision.face.detected":
            count = int(
                payload.get("count", 0)
            )

            self.set_state(
                "excited",
                f"Vision detected {count} face"
                f"{'' if count == 1 else 's'}.",
            )

        elif event_type == "vision.qr.detected":
            count = int(
                payload.get("count", 0)
            )

            self.set_state(
                "success",
                f"Vision detected {count} QR code"
                f"{'' if count == 1 else 's'}.",
            )

        elif event_type == "face.state":
            state = str(
                payload.get("state", "idle")
            )

            message = str(
                payload.get("message", "")
            )
 
            self.set_state(
                state,
                message or None,
            )

        elif event_type == "notification":
            level = str(
                payload.get("level", "info")
            ).lower()

            title = str(
                payload.get("title", "Buster")
            )

            message = str(
                payload.get("message", "")
            )

            state_map = {
                "success": "success",
                "warning": "warning",
                "error": "error",
                "danger": "error",
                "info": "speaking",
            }

            self.set_state(
                state_map.get(level, "speaking"),
                f"{title}: {message}",
            )

        self.refresh_runtime()   


    def _handle_voice_event(
        self,
        payload: dict,
    ) -> None:
        status = str(
             payload.get("status", "ready")
        ).lower()

        if status in {
            "recording",
            "listening",
        }:
            self.set_state(
                "listening",
                "Listening for your voice command.",
            )

        elif status == "speaking":
            self.set_state(
                "speaking",
                "Buster is speaking.",
            )

        elif status in {
            "processing",
            "transcribing",
        }:
            self.set_state(
                "thinking",
                "Processing recorded speech.",
            )

        elif status == "error":
            self.set_state(
                "error",
                str(
                    payload.get(
                        "message",
                        "Voice service error.",
                    )
                ),
            )

        elif status in {
            "ready",
            "idle",
            "stopped",
        }:
            self._return_to_runtime_state()


    def _handle_vision_event(
        self,
        payload: dict,
    ) -> None:
        status = str(
            payload.get("status", "ready")
        ).lower()

        if status in {
            "running",
            "active",
        }:
            self.set_state(
                "working",
                "Vision camera is active.",
            )

        elif status == "tracking":
            self.set_state(
                "thinking",
                "Vision is tracking activity.",
            )

        elif status == "error":
            self.set_state(
                "error",
                str(
                    payload.get(
                        "message",
                        "Vision service error.",
                    )
                ),
            )

        elif status in {
            "ready",
            "idle",
            "stopped",
        }:
            self._return_to_runtime_state()   


    def _return_to_runtime_state(self) -> None:
        if self.manual_state:
            return

        if not self.runtime_core:
            self.set_state(
                "idle",
                "Buster is ready.",
            )
            return

        state_store = getattr(
            self.runtime_core,
            "state",
            None,
        )

        if state_store is None:
            self.set_state(
                "idle",
                "Buster is ready.",
            )
            return

        face_state = state_store.get(
            "face",
            {},
        )

        self.set_state(
            face_state.get("state", "idle"),
            face_state.get(
                "message",
                "Buster is ready.",
            ),
        )      

        
