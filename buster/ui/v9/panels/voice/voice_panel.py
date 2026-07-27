"""
voice_panel.py - Main Voice Interface Panel
Integrates AudioEngine and AudioVisualizer modules with safe cross-thread signals.
"""

import os
import json
import threading
from pathlib import Path

from PySide6.QtCore import Slot, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QSplitter, QFrame, QStatusBar, QSlider, QComboBox, QMessageBox
)

# Relative imports from local package
from .audio_engine import AudioEngine, VoiceProfile, VoiceState, PYAUDIO_AVAILABLE
from .audio_visualizer import AudioVisualizer


class VoicePanel(QWidget):
    """Main voice control panel widget"""

    # Thread-safe GUI signal updates
    status_update_signal = Signal(str)
    info_append_signal = Signal(str)
    text_set_signal = Signal(str)
    error_signal = Signal(str)
    voice_finished_signal = Signal()

    def __init__(self, live=None, runtime_core=None, parent=None):
        super().__init__(parent)

        self.live = live
        self.runtime_core = runtime_core

        try:
            self.audio_engine = AudioEngine()
        except Exception as e:
            QMessageBox.warning(self, "Voice Error", f"Voice engine unavailable:\n\n{e}")
            self.audio_engine = None

        self.voice_service = self._resolve_voice_service()
        self._runtime_subscriptions = []

        self.voice_profile = VoiceProfile()
        self.current_state = VoiceState.IDLE
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_duration = 0

        self.setup_ui()
        self.connect_signals()
        self._connect_runtime_audio_events()
        self.load_settings()
        self.apply_dark_theme()

    def setup_ui(self):
        """Construct widget layout"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("🎤 Buster Voice")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_indicator = QLabel("● Ready")
        self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)

        self.device_label = QLabel("🎙️ Default")
        self.device_label.setStyleSheet("color: #569cd6; font-weight: bold; margin-left: 8px;")
        header_layout.addWidget(self.device_label)
        layout.addWidget(header_widget)

        # Content Splitter
        content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(content_splitter, 1)

        # Audio Visualizer
        self.visualizer = AudioVisualizer()
        self.visualizer.setMinimumHeight(200)
        content_splitter.addWidget(self.visualizer)

        # Bottom Control Section
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(8)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Controls Row
        record_layout = QHBoxLayout()

        self.record_btn = QPushButton("🔴 Record")
        self.record_btn.setStyleSheet(self.get_button_style("#f44747"))
        self.record_btn.clicked.connect(self.toggle_recording)
        record_layout.addWidget(self.record_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self.get_button_style("#888888"))
        self.stop_btn.clicked.connect(self.stop_recording)
        record_layout.addWidget(self.stop_btn)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("QFrame { background:#444; min-width:1px; max-width:1px; }")
        record_layout.addWidget(separator)

        self.recording_time_label = QLabel("00:00")
        self.recording_time_label.setStyleSheet("""
            color: #f44747;
            font-size: 14pt;
            font-weight: bold;
            font-family: 'Consolas', monospace;
        """)
        record_layout.addWidget(self.recording_time_label)

        record_layout.addStretch()

        self.tts_btn = QPushButton("🔊 Speak")
        self.tts_btn.setStyleSheet(self.get_button_style("#4ec9b0"))
        self.tts_btn.clicked.connect(self.speak_text)
        record_layout.addWidget(self.tts_btn)

        self.stt_btn = QPushButton("📝 Transcribe")
        self.stt_btn.setStyleSheet(self.get_button_style("#569cd6"))
        self.stt_btn.clicked.connect(self.transcribe_audio)
        record_layout.addWidget(self.stt_btn)

        self.live_listen_btn = QPushButton("🎧 Live Listen")
        self.live_listen_btn.setCheckable(True)
        self.live_listen_btn.setStyleSheet(
            self.get_button_style("#dcdcaa")
        )
        self.live_listen_btn.clicked.connect(
            self.toggle_streaming_stt
        )
        record_layout.addWidget(self.live_listen_btn)

        self.wake_word_btn = QPushButton("⭐ Hey Buster")
        self.wake_word_btn.setCheckable(True)
        self.wake_word_btn.setStyleSheet(
            self.get_button_style("#c586c0")
        )
        self.wake_word_btn.clicked.connect(
            self.toggle_wake_word
        )
        record_layout.addWidget(self.wake_word_btn)

        bottom_layout.addLayout(record_layout)

        # Text Area
        text_widget = QWidget()
        text_layout = QHBoxLayout(text_widget)
        text_layout.setSpacing(8)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to speak or paste text for TTS...")
        self.text_input.setMaximumHeight(80)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 4px;
                font-size: 10pt;
            }
            QTextEdit:focus { border-color: #4ec9b0; }
        """)
        text_layout.addWidget(self.text_input)
        bottom_layout.addWidget(text_widget)

        # Settings & Console Info Row
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(80)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
        """)
        info_layout.addWidget(self.info_text)

        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(2)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # Speed Slider
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 300)
        self.speed_slider.setValue(180)
        self.speed_slider.valueChanged.connect(self.update_voice_settings)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("180")
        speed_layout.addWidget(self.speed_label)
        settings_layout.addLayout(speed_layout)

        # Volume Slider
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self.update_voice_settings)
        volume_layout.addWidget(self.volume_slider)
        self.volume_label = QLabel("80%")
        volume_layout.addWidget(self.volume_label)
        settings_layout.addLayout(volume_layout)

        # Mode Selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Waveform", "Spectrum", "Spectrogram"])
        self.mode_combo.currentTextChanged.connect(self.change_visualization_mode)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        settings_layout.addLayout(mode_layout)

        info_layout.addWidget(settings_widget)
        bottom_layout.addWidget(info_widget)

        content_splitter.addWidget(bottom_widget)
        content_splitter.setSizes([300, 400])

        # Footer Status Bar
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                color: #888888;
                border-top: 1px solid #333333;
                padding: 2px 5px;
            }
        """)
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)

        self.quality_label = QLabel("🎙️ High Quality")
        status_bar.addPermanentWidget(self.quality_label)
        status_bar.addPermanentWidget(QLabel("✨ Voice v1.0"))
        layout.addWidget(status_bar)

    def connect_signals(self):
        """Bind underlying engine events to UI updates"""
        if not self.audio_engine:
            return

        self.audio_engine.audio_data_ready.connect(self.visualizer.update_data)
        self.audio_engine.recording_finished.connect(self.on_recording_finished)
        self.audio_engine.status_changed.connect(self.update_status)
        self.audio_engine.error_occurred.connect(self.show_error)

        self.status_update_signal.connect(self.update_status)
        self.info_append_signal.connect(self.info_text.append)
        self.text_set_signal.connect(self.text_input.setPlainText)
        self.error_signal.connect(self.show_error)
        self.voice_finished_signal.connect(self.voice_finished)


    def _resolve_voice_service(self):
        runtime = self.runtime_core
        if runtime is None:
            return None

        for name in ("voice_service", "audio_service"):
            service = getattr(runtime, name, None)
            if service is not None:
                return service

        services = getattr(runtime, "services", None)
        if services is None:
            return None

        for name in ("voice", "audio"):
            if isinstance(services, dict):
                service = services.get(name)
            else:
                service = None
                for method_name in ("get", "resolve", "service"):
                    method = getattr(services, method_name, None)
                    if callable(method):
                        try:
                            service = method(name)
                        except Exception:
                            service = None
                        if service is not None:
                            break
            if service is not None:
                return service

        return None

    def _connect_runtime_audio_events(self):
        if not self.runtime_core:
            return

        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        subscribe = getattr(dispatcher, "subscribe", None)
        if not callable(subscribe):
            return

        handlers = {
            "audio.transcription.started": self._on_runtime_transcription_started,
            "audio.transcription.completed": self._on_runtime_transcription_completed,
            "audio.tts.started": self._on_runtime_tts_started,
            "audio.tts.completed": self._on_runtime_tts_completed,
            "audio.error": self._on_runtime_audio_error,
            "audio.streaming.started": self._on_streaming_started,
            "audio.streaming.stopped": self._on_streaming_stopped,
            "audio.streaming.speech_started": self._on_streaming_speech_started,
            "audio.streaming.transcription_final": self._on_streaming_transcription_final,
            "audio.streaming.level": self._on_streaming_level,
            "audio.wake_word.enabled": self._on_wake_word_enabled,
            "audio.wake_word.disabled": self._on_wake_word_disabled,
            "audio.wake_word.detected": self._on_wake_word_detected,
            "audio.wake_word.awaiting_command": self._on_wake_word_awaiting_command,
            "audio.wake_word.command": self._on_wake_word_command,
            "audio.wake_word.command_timeout": self._on_wake_word_timeout,
            "audio.whisper.warmup.started": self._on_whisper_warmup_started,
            "audio.whisper.warmup.completed": self._on_whisper_warmup_completed,
            "audio.streaming.transcription_dropped": self._on_streaming_transcription_dropped,
            "voice.state.changed": self._on_voice_state_changed,
            "audio.tts.interrupted": self._on_tts_interrupted,
        }

        for topic, handler in handlers.items():
            try:
                unsubscribe = subscribe(topic, handler)
                if callable(unsubscribe):
                    self._runtime_subscriptions.append(unsubscribe)
            except Exception:
                continue

    @staticmethod
    def _event_payload(event):
        if isinstance(event, dict):
            payload = event.get("payload", event)
            return payload if isinstance(payload, dict) else {}
        payload = getattr(event, "payload", None)
        return payload if isinstance(payload, dict) else {}

    def _publish_audio_request(self, topic: str, payload: dict) -> bool:
        if not self.runtime_core:
            return False
        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        publish = getattr(dispatcher, "publish", None)
        if not callable(publish):
            return False
        try:
            publish(topic, payload, source="voice_panel")
        except TypeError:
            publish(topic, payload)
        return True

    def _on_runtime_transcription_started(self, event):
        payload = self._event_payload(event)
        filename = payload.get("audio_file", "")
        self.status_update_signal.emit("Local Whisper transcription started...")
        self.info_append_signal.emit(
            f"🧠 Local Whisper processing: {os.path.basename(filename)}"
        )

    def _on_runtime_transcription_completed(self, event):
        payload = self._event_payload(event)
        text = str(payload.get("text", "")).strip()
        if text:
            self.text_set_signal.emit(text)
            self.info_append_signal.emit(
                f"✅ [{payload.get('backend', 'local-stt')}] {text}"
            )
            self.status_update_signal.emit("Transcription complete")
            self.publish_face_state("speaking", "Voice command understood.")
        elif payload.get("speech_detected") is False:
            self.info_append_signal.emit("⚠️ No speech detected in recording.")
            self.status_update_signal.emit("No speech detected")
        else:
            self.info_append_signal.emit("⚠️ Transcription returned no text.")
            self.status_update_signal.emit("No transcription text")

    def _on_runtime_tts_started(self, event):
        self.status_update_signal.emit("Speaking...")
        self.publish_face_state("speaking", "Speaking response.")

    def _on_runtime_tts_completed(self, event):
        payload = self._event_payload(event)
        self.status_update_signal.emit("Speech complete")
        self.info_append_signal.emit(
            f"✅ TTS complete via {payload.get('backend', 'voice service')}"
        )
        self.publish_face_state("idle", "Voice response completed.")
        self.voice_finished_signal.emit()

    def _on_runtime_audio_error(self, event):
        payload = self._event_payload(event)
        self.error_signal.emit(
            str(payload.get("error") or "Unknown audio service error")
        )


    @Slot()
    def toggle_streaming_stt(self):
        topic = (
            "audio.streaming.stop.requested"
            if self.live_listen_btn.isChecked() is False
            else "audio.streaming.start.requested"
        )
        if not self._publish_audio_request(topic, {}):
            self.live_listen_btn.setChecked(False)
            self.show_error(
                "Runtime StreamingSTTService is unavailable."
            )

    def _on_streaming_started(self, event):
        self.live_listen_btn.setChecked(True)
        self.live_listen_btn.setText("⏹ Stop Listening")
        self.status_update_signal.emit("Live listening...")
        self.info_append_signal.emit(
            "🎧 Streaming STT started."
        )
        self.publish_face_state(
            "listening",
            "Buster is listening continuously.",
        )

    def _on_streaming_stopped(self, event):
        self.live_listen_btn.setChecked(False)
        self.live_listen_btn.setText("🎧 Live Listen")
        self.status_update_signal.emit("Ready")
        self.info_append_signal.emit(
            "⏹ Streaming STT stopped."
        )
        self.publish_face_state(
            "idle",
            "Continuous listening stopped.",
        )

    def _on_streaming_speech_started(self, event):
        self.status_update_signal.emit("Speech detected...")
        self.publish_face_state(
            "listening",
            "Speech detected.",
        )

    def _on_streaming_transcription_final(self, event):
        payload = self._event_payload(event)
        text = str(payload.get("text", "")).strip()
        if not text:
            return

        self.text_set_signal.emit(text)
        self.info_append_signal.emit(
            f"🎧 {text}"
        )
        self.status_update_signal.emit(
            "Live transcription complete"
        )

    def _on_streaming_level(self, event):
        payload = self._event_payload(event)
        samples = payload.get("samples")
        if not samples:
            return
        try:
            import numpy as np
            self.visualizer.update_data(
                np.asarray(samples, dtype=np.int16)
            )
        except Exception:
            pass


    @Slot()
    def toggle_wake_word(self):
        enabled = self.wake_word_btn.isChecked()
        topic = (
            "audio.wake_word.enable.requested"
            if enabled
            else "audio.wake_word.disable.requested"
        )
        if not self._publish_audio_request(topic, {}):
            self.wake_word_btn.setChecked(False)
            self.show_error("Runtime WakeWordService is unavailable.")
            return

        if enabled and not self.live_listen_btn.isChecked():
            self.live_listen_btn.setChecked(True)
            self.toggle_streaming_stt()

    def _on_wake_word_enabled(self, event):
        payload = self._event_payload(event)
        phrases = payload.get("wake_phrases") or ["hey buster"]
        phrase = phrases[0]
        self.wake_word_btn.setChecked(True)
        self.wake_word_btn.setText("⭐ Wake Word On")
        self.status_update_signal.emit(f'Waiting for "{phrase}"...')
        self.info_append_signal.emit(f'⭐ Wake word enabled: "{phrase}"')
        self.publish_face_state("listening", f'Waiting for "{phrase}".')

    def _on_wake_word_disabled(self, event):
        self.wake_word_btn.setChecked(False)
        self.wake_word_btn.setText("⭐ Hey Buster")
        self.status_update_signal.emit("Wake word off")
        self.info_append_signal.emit("Wake word disabled.")

    def _on_wake_word_detected(self, event):
        payload = self._event_payload(event)
        phrase = payload.get("wake_phrase", "hey buster")
        self.status_update_signal.emit("Wake word detected")
        self.info_append_signal.emit(f'⭐ Detected: "{phrase}"')
        self.publish_face_state("attention", "Wake word detected.")

    def _on_wake_word_awaiting_command(self, event):
        self.status_update_signal.emit("Listening for command...")
        self.info_append_signal.emit("🎤 Listening for your command.")
        self.publish_face_state("listening", "Listening for command.")

    def _on_wake_word_command(self, event):
        payload = self._event_payload(event)
        command = str(
            payload.get("command")
            or payload.get("text")
            or ""
        ).strip()
        if not command:
            return

        self.text_set_signal.emit(command)
        self.info_append_signal.emit(f"⭐ Command: {command}")
        self.status_update_signal.emit("Wake command received")
        self.publish_face_state("thinking", "Processing voice command.")

    def _on_wake_word_timeout(self, event):
        self.status_update_signal.emit('Waiting for "Hey Buster"...')
        self.info_append_signal.emit("Wake command timed out.")
        self.publish_face_state("idle", "Wake command timed out.")


    def _on_whisper_warmup_started(self, event):
        self.info_append_signal.emit(
            "🧠 Loading local Whisper model in the background..."
        )

    def _on_whisper_warmup_completed(self, event):
        payload = self._event_payload(event)
        backend = payload.get("backend") or "local Whisper"
        self.info_append_signal.emit(
            f"✅ {backend} is warmed up and ready."
        )

    def _on_streaming_transcription_dropped(self, event):
        self.info_append_signal.emit(
            "⚠️ Voice command skipped because transcription was busy."
        )


    def _on_voice_state_changed(self, event):
        payload = self._event_payload(event)
        state = str(payload.get("state", "idle"))

        labels = {
            "idle": "Ready",
            "listening": "Listening...",
            "wake_detected": "Wake word detected",
            "thinking": "Thinking...",
            "speaking": "Speaking...",
            "interrupted": "Interrupted",
            "error": "Voice error",
        }

        label = labels.get(
            state,
            state.replace("_", " ").title(),
        )
        self.status_update_signal.emit(label)

        face_states = {
            "idle": "idle",
            "listening": "listening",
            "wake_detected": "attention",
            "thinking": "thinking",
            "speaking": "speaking",
            "interrupted": "listening",
            "error": "error",
        }

        self.publish_face_state(
            face_states.get(state, "idle"),
            label,
        )


    def _on_tts_interrupted(self, event):
        self.info_append_signal.emit(
            "⏸ Speech playback stopped."
        )
        self.status_update_signal.emit(
            "Interrupted"
        )

    def apply_dark_theme(self):
        """Apply Buster global dark stylesheet"""
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI', sans-serif; }
            QPushButton { background-color: #2d2d2d; color: #cccccc; border: none; padding: 6px 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555555; }
            QSlider::groove:horizontal { background-color: #333333; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background-color: #4ec9b0; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
            QComboBox { background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #333333; border-radius: 4px; padding: 4px 8px; }
            QSplitter::handle { background-color: #333333; }
        """)

    def get_button_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: #1e1e1e;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {color}cc; }}
            QPushButton:disabled {{ background-color: #555555; color: #888888; }}
        """

    def publish_voice_status(self, status: str, **extra):
        if not self.runtime_core:
            return
        payload = {"status": status, **extra}
        self.runtime_core.dispatcher.publish("voice.status", payload, source="voice_panel")

    def publish_face_state(self, state: str, message: str):
        if not self.runtime_core:
            return
        self.runtime_core.dispatcher.face(state, message)

    @Slot()
    def toggle_recording(self):
        if self.current_state == VoiceState.IDLE:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if not PYAUDIO_AVAILABLE:
            self.show_error("PyAudio is not installed. Run: pip install pyaudio")
            return
        if not self.audio_engine:
            self.show_error("Audio engine is unavailable.")
            return

        self.audio_engine.start_recording()
        self.current_state = VoiceState.RECORDING
        self.record_btn.setText("⏹ Stop")
        self.record_btn.setStyleSheet(self.get_button_style("#f44747"))
        self.stop_btn.setEnabled(True)
        self.recording_duration = 0
        self.recording_timer.start(1000)

        self.publish_voice_status("recording", device="default")
        self.publish_face_state("listening", "Listening for your voice command.")
        self.update_status("Recording...")
        self.info_text.append("🎙️ Recording started...")

    @Slot()
    def stop_recording(self):
        if self.audio_engine:
            self.audio_engine.stop_recording()

        self.current_state = VoiceState.IDLE
        self.record_btn.setText("🔴 Record")
        self.record_btn.setStyleSheet(self.get_button_style("#f44747"))
        self.stop_btn.setEnabled(False)
        self.recording_timer.stop()
        self.recording_time_label.setText("00:00")

        self.publish_voice_status("ready")
        self.publish_face_state("idle", "Voice recording stopped.")
        self.update_status("Recording stopped")
        self.info_text.append("⏹ Recording stopped")

    def on_recording_finished(self, filename: str):
        self.info_text.append(f"💾 Recording saved: {os.path.basename(filename)}")
        self.update_status(f"Recording saved: {os.path.basename(filename)}")

    @Slot()
    def update_recording_time(self):
        self.recording_duration += 1
        minutes = self.recording_duration // 60
        seconds = self.recording_duration % 60
        self.recording_time_label.setText(f"{minutes:02d}:{seconds:02d}")

    @Slot()
    @Slot()
    def speak_text(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            text = self.info_text.toPlainText().strip()
        if not text:
            self.show_error("No text to speak")
            return

        payload = {
            "text": text,
            "rate": self.voice_profile.rate,
            "volume": self.voice_profile.volume,
            "voice": None if self.voice_profile.voice == "default" else self.voice_profile.voice,
            "prefer_edge": True,
        }

        if self._publish_audio_request("audio.tts.requested", payload):
            self.current_state = VoiceState.PLAYING
            self.status_update_signal.emit("TTS request sent...")
            self.info_append_signal.emit(
                "🔊 Sent speech request to runtime VoiceService."
            )
            return

        if self.voice_service is not None:
            try:
                self.voice_service.speak_async(text, **payload)
                return
            except Exception as exc:
                self.show_error(str(exc))
                return

        if self.audio_engine:
            threading.Thread(
                target=self.audio_engine.synthesize_speech,
                args=(text, self.voice_profile),
                daemon=True,
            ).start()

    def _speak_thread(self, text: str):
        if not self.audio_engine:
            self.error_signal.emit("Voice engine unavailable.")
            return

        try:
            self.audio_engine.synthesize_speech(text, self.voice_profile)
            self.current_state = VoiceState.IDLE
            self.status_update_signal.emit("Ready")
            self.info_append_signal.emit(f"🔊 Spoke: {text[:50]}...")
            self.voice_finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(f"TTS error: {e}")
            self.voice_finished_signal.emit()

    @Slot()
    def voice_finished(self):
        self.tts_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.stt_btn.setEnabled(True)
        self.publish_voice_status("ready")
        self.publish_face_state("idle", "Buster is ready.")

    @Slot()
    @Slot()
    def transcribe_audio(self):
        recordings_dir = Path("recordings")
        recordings = sorted(
            recordings_dir.glob("*.wav"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not recordings:
            self.show_error(
                "No recording found. Record audio before transcribing."
            )
            return

        latest = recordings[0]
        payload = {
            "audio_file": str(latest.resolve()),
            "language": self.voice_profile.language,
            "require_speech": True,
        }

        if self._publish_audio_request(
            "audio.transcribe.requested",
            payload,
        ):
            self.current_state = VoiceState.PROCESSING
            self.status_update_signal.emit(
                "Local Whisper request sent..."
            )
            return

        if self.voice_service is not None:
            try:
                self.voice_service.transcribe_async(
                    latest,
                    language=self.voice_profile.language,
                    require_speech=True,
                )
                return
            except Exception as exc:
                self.show_error(str(exc))
                return

        self.show_error(
            "Runtime VoiceService is unavailable. Restart Buster after "
            "installing the audio runtime upgrade."
        )

    def _transcribe_thread(self, audio_file: str = None):
        if not self.audio_engine:
            self.error_signal.emit("Voice engine unavailable.")
            return

        try:
            if not audio_file:
                recordings = list(self.audio_engine.recording_path.glob("*.wav"))
                if recordings:
                    audio_file = str(sorted(recordings)[-1])
                else:
                    self.error_signal.emit("No audio file to transcribe")
                    return

            text = self.audio_engine.recognize_speech(audio_file)
            if text:
                self.text_set_signal.emit(text)
                self.info_append_signal.emit(f"📝 Transcribed: {text[:100]}...")
                self.status_update_signal.emit("Transcription complete")

                if self.runtime_core:
                    self.runtime_core.dispatcher.publish(
                        "voice.transcribed",
                        {"text": text, "audio_file": audio_file},
                        source="voice_panel",
                    )
                    self.runtime_core.dispatcher.notify("Voice", "Speech transcription completed.", "success")
            else:
                self.error_signal.emit("No speech recognized")

            self.current_state = VoiceState.IDLE
            self.status_update_signal.emit("Ready")

        except Exception as e:
            self.error_signal.emit(f"Transcription error: {str(e)}")
            self.current_state = VoiceState.IDLE

    @Slot()
    def update_voice_settings(self):
        speed = self.speed_slider.value()
        volume = self.volume_slider.value()

        self.speed_label.setText(str(speed))
        self.volume_label.setText(f"{volume}%")

        self.voice_profile.rate = speed
        self.voice_profile.volume = volume / 100.0
        self.update_status(f"Settings updated: {speed} WPM, {volume}% volume")

    @Slot(str)
    def change_visualization_mode(self, mode: str):
        mode_map = {"Waveform": "waveform", "Spectrum": "spectrum", "Spectrogram": "spectrogram"}
        self.visualizer.set_mode(mode_map.get(mode, "waveform"))
        self.update_status(f"Visualization mode: {mode}")

    @Slot(str)
    def update_status(self, status: str):
        self.status_label.setText(status)
        if "error" in status.lower():
            self.status_indicator.setText("● Error")
            self.status_indicator.setStyleSheet("color: #f44747; font-weight: bold;")
        elif "recording" in status.lower():
            self.status_indicator.setText("● Recording")
            self.status_indicator.setStyleSheet("color: #f44747; font-weight: bold;")
        elif "speaking" in status.lower() or "processing" in status.lower():
            self.status_indicator.setText("● Processing")
            self.status_indicator.setStyleSheet("color: #dcdcaa; font-weight: bold;")
        else:
            self.status_indicator.setText("● Ready")
            self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")

    @Slot(str)
    def show_error(self, error: str):
        self.info_text.append(f"❌ Error: {error}")
        self.update_status(f"Error: {error}")
        self.status_indicator.setText("● Error")
        self.status_indicator.setStyleSheet("color:#f44747; font-weight:bold;")
        self.current_state = VoiceState.ERROR

        self.publish_voice_status("error", message=error)
        self.publish_face_state("error", error)

        QMessageBox.warning(self, "Voice Error", error)

    def load_settings(self):
        settings_file = Path("voice_settings.json")
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                self.speed_slider.setValue(settings.get('speed', 180))
                self.volume_slider.setValue(settings.get('volume', 80))
                self.voice_profile.rate = settings.get('speed', 180)
                self.voice_profile.volume = settings.get('volume', 80) / 100.0
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save_settings(self):
        settings = {'speed': self.speed_slider.value(), 'volume': self.volume_slider.value()}
        try:
            with open("voice_settings.json", 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def closeEvent(self, event):
        for unsubscribe in getattr(self, "_runtime_subscriptions", []):
            try:
                unsubscribe()
            except Exception:
                pass
        self._runtime_subscriptions = []
        self.save_settings()
        self.recording_timer.stop()
        if self.audio_engine:
            self.audio_engine.requestInterruption()
            self.audio_engine.stop_recording()
            self.audio_engine.quit()
            self.audio_engine.wait(2000)
        event.accept()