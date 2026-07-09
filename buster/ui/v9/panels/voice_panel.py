#!/usr/bin/env python3
"""
voice_panel.py - Buster Voice Panel with PySide6
A comprehensive voice processing panel with TTS, STT, recording, and visualization.
"""

import sys
import os
import json
import time
import threading
import wave

import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
from PySide6.QtMultimediaWidgets import *

# Try to import speech recognition and TTS libraries
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    PYAUDIO_AVAILABLE = False    
# ==================== Data Models ====================

class VoiceState(Enum):
    """Voice system states"""
    IDLE = "idle"
    RECORDING = "recording"
    PLAYING = "playing"
    PROCESSING = "processing"
    ERROR = "error"

class VoiceProfile:
    """Voice profile settings"""
    def __init__(self):
        self.name = "Default"
        self.voice = "default"
        self.rate = 180  # Words per minute
        self.volume = 0.8
        self.pitch = 1.0
        self.language = "en-US"
        self.auto_save = True

# ==================== Audio Engine ====================

class AudioEngine(QThread):
    """Background thread for audio processing"""
    
    audio_data_ready = Signal(np.ndarray)
    recording_finished = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.is_playing = False
        self.audio_data = []
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 1024
        if PYAUDIO_AVAILABLE:
            self.format = pyaudio.paInt16
            self.p = pyaudio.PyAudio()
        else:
            self.format = None
            self.p = None
        self.stream = None
        self.mutex = QMutex()
        
        # TTS engine
        self.tts_engine = None
        if TTS_AVAILABLE:
            self.tts_engine = pyttsx3.init()
            self.setup_tts()
        
        # Speech recognizer
        self.recognizer = None
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
        
        # Recording parameters
        self.recording_path = Path("recordings")
        self.recording_path.mkdir(exist_ok=True)
        
        # Visualization
        self.visualization_data = np.zeros(1024)
        self.fft_data = np.zeros(512)
        
    def setup_tts(self):
        """Setup TTS engine"""
        if self.tts_engine:
            voices = self.tts_engine.getProperty('voices')
            if voices:
                self.tts_engine.setProperty('voice', voices[0].id)
            self.tts_engine.setProperty('rate', 180)
            self.tts_engine.setProperty('volume', 0.8)
    
    def start_recording(self):
        """Start audio recording"""
        if not PYAUDIO_AVAILABLE or self.p is None:
            self.error_occurred.emit(
                "PyAudio is not available."
            )
            return

        self.mutex.lock()
        try:
            if self.is_recording:
                return
            
            self.audio_data = []
            self.is_recording = True
            
            # Open audio stream
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.status_changed.emit("Recording started...")
            
        except Exception as e:
            self.error_occurred.emit(f"Error starting recording: {str(e)}")
            self.is_recording = False
        finally:
            self.mutex.unlock()
    
    def stop_recording(self):
        """Stop audio recording"""
        self.mutex.lock()
        try:
            if not self.is_recording:
                return
            
            self.is_recording = False
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Save recording
            if self.audio_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = self.recording_path / f"recording_{timestamp}.wav"
                self._save_wave(str(filename), self.audio_data)
                self.recording_finished.emit(str(filename))
                self.status_changed.emit(f"Recording saved: {filename.name}")
            
        except Exception as e:
            self.error_occurred.emit(f"Error stopping recording: {str(e)}")
        finally:
            self.mutex.unlock()
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for recording"""
        if self.is_recording:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            self.audio_data.append(audio_data)
            
            # Update visualization data
            self.visualization_data = audio_data[:1024] if len(audio_data) >= 1024 else np.pad(audio_data, (0, 1024 - len(audio_data)))
            self.fft_data = np.abs(np.fft.fft(self.visualization_data))[:512]
            self.audio_data_ready.emit(self.visualization_data)
            
        if PYAUDIO_AVAILABLE:
            return (in_data, pyaudio.paContinue)

        return (None, 0)
    
    def _save_wave(self, filename: str, audio_data: List[np.ndarray]):
        """Save audio data as WAV file"""
        try:
            audio_bytes = b''.join([data.tobytes() for data in audio_data])
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                
                # FIXED: Check if audio device is available before calling get_sample_size
                if self.p is None or self.format is None:
                    self.error_occurred.emit(
                        "Audio device unavailable."
                    )
                    return

                wf.setsampwidth(
                    self.p.get_sample_size(self.format)
                )
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_bytes)
                
        except Exception as e:
            self.error_occurred.emit(f"Error saving file: {str(e)}")
    
    def synthesize_speech(self, text: str, voice_profile: VoiceProfile = None):
        """Synthesize speech from text"""
        if not TTS_AVAILABLE or not self.tts_engine:
            self.error_occurred.emit("TTS engine not available")
            return
        
        try:
            self.status_changed.emit("Synthesizing speech...")
            
            # Update TTS settings
            if voice_profile:
                self.tts_engine.setProperty('rate', voice_profile.rate)
                self.tts_engine.setProperty('volume', voice_profile.volume)
            
            # Synthesize
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
            self.status_changed.emit("Speech synthesis complete")
            
        except Exception as e:
            self.error_occurred.emit(f"Error synthesizing speech: {str(e)}")
    
    def recognize_speech(self, audio_file: str = None) -> str:
        """Recognize speech from audio file or microphone"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.error_occurred.emit("Speech recognition not available")
            return ""
        
        try:
            self.status_changed.emit("Recognizing speech...")
            
            if audio_file:
                # Recognize from file
                with sr.AudioFile(audio_file) as source:
                    audio = self.recognizer.record(source)
            else:
                # Recognize from microphone (requires microphone access)
                with sr.Microphone() as source:
                    self.status_changed.emit("Listening...")
                    audio = self.recognizer.listen(source)
            
            # Recognize using Google Speech Recognition
            text = self.recognizer.recognize_google(audio, language="en-US")
            self.status_changed.emit("Speech recognition complete")
            return text
            
        except sr.UnknownValueError:
            self.error_occurred.emit("Could not understand audio")
            return ""
        except sr.RequestError as e:
            self.error_occurred.emit(f"Speech recognition service error: {str(e)}")
            return ""
        except Exception as e:
            self.error_occurred.emit(f"Speech recognition error: {str(e)}")
            return ""
    
    def run(self):
        """Main loop for background processing"""
        while True:
            self.msleep(100)
    
    def __del__(self):
        """Cleanup resources"""
        if self.stream:
            self.stream.close()
        if self.p:
            self.p.terminate()

# ==================== Audio Visualizer ====================

class AudioVisualizer(QWidget):
    """Widget for audio visualization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_data = np.zeros(1024)
        self.fft_data = np.zeros(512)
        self.mode = "waveform"  # waveform, spectrum, spectrogram
        self.setMinimumHeight(150)
        self.setMinimumWidth(400)
        
    def update_data(self, audio_data: np.ndarray):
        """Update audio data for visualization"""
        self.audio_data = audio_data[:1024]
        self.fft_data = np.abs(np.fft.fft(self.audio_data))[:512]
        self.update()
    
    def set_mode(self, mode: str):
        """Set visualization mode"""
        self.mode = mode
        self.update()
    
    def paintEvent(self, event):
        """Paint the visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        if self.mode == "waveform":
            self._draw_waveform(painter)
        elif self.mode == "spectrum":
            self._draw_spectrum(painter)
        elif self.mode == "spectrogram":
            self._draw_spectrogram(painter)
        
    def _draw_waveform(self, painter):
        """Draw waveform visualization"""
        if len(self.audio_data) < 2:
            return
        
        width = self.width()
        height = self.height()
        center_y = height // 2
        
        # Normalize data
        max_val = np.max(np.abs(self.audio_data)) or 1
        normalized = self.audio_data / max_val
        
        # Draw wave
        step = len(normalized) // width
        if step == 0:
            step = 1
        
        painter.setPen(QPen(QColor(78, 201, 176), 2))
        
        points = []
        for i in range(0, len(normalized), step):
            x = int(i / len(normalized) * width)
            y = int(center_y + normalized[i] * height * 0.4)
            points.append(QPoint(x, y))
        
        # Draw connected lines
        if len(points) > 1:
            painter.drawPolyline(points)
        
        # Draw glow effect
        glow_color = QColor(78, 201, 176, 50)
        painter.setPen(QPen(glow_color, 8))
        painter.drawPolyline(points)
    
    def _draw_spectrum(self, painter):
        """Draw frequency spectrum"""
        if len(self.fft_data) < 2:
            return
        
        width = self.width()
        height = self.height()
        
        # Normalize
        max_val = np.max(self.fft_data) or 1
        normalized = self.fft_data / max_val
        
        # Draw bars
        bar_width = width / len(normalized)
        
        for i, value in enumerate(normalized):
            x = int(i * bar_width)
            bar_height = int(value * height * 0.8)
            y = height - bar_height
            
            # Color gradient based on frequency
            intensity = value * 255
            color = QColor(
                int(78 + intensity * 0.5),
                int(201 - intensity * 0.3),
                int(176 - intensity * 0.4)
            )
            
            painter.fillRect(x, y, max(1, int(bar_width)), bar_height, color)
    
    def _draw_spectrogram(self, painter):
        """Draw spectrogram (simplified)"""
        if len(self.fft_data) < 2:
            return
        
        width = self.width()
        height = self.height()
        
        # Normalize
        max_val = np.max(self.fft_data) or 1
        normalized = self.fft_data / max_val
        
        # Draw as heatmap bars
        bar_width = width / len(normalized)
        
        for i, value in enumerate(normalized):
            x = int(i * bar_width)
            bar_height = int(value * height * 0.8)
            y = height - bar_height
            
            # Heatmap colors
            if value > 0.8:
                color = QColor(255, 0, 0)
            elif value > 0.6:
                color = QColor(255, 128, 0)
            elif value > 0.4:
                color = QColor(255, 255, 0)
            elif value > 0.2:
                color = QColor(0, 255, 0)
            else:
                color = QColor(0, 128, 255)
            
            painter.fillRect(x, y, max(1, int(bar_width)), bar_height, color)

# ==================== Voice Panel ====================

class VoicePanel(QWidget):
    """Main voice panel widget"""

    # FIXED: Added signals for thread-safe GUI updates
    status_update_signal = Signal(str)
    info_append_signal = Signal(str)
    text_set_signal = Signal(str)
    error_signal = Signal(str)
    voice_finished_signal = Signal()

    def __init__(self, live=None, parent=None, runtime_core=None):
        super().__init__(parent)

        self.live = live
        
        # FIXED: Connect signals to slots for thread-safe GUI updates
        self.status_update_signal.connect(self.update_status)
        self.info_append_signal.connect(self._append_info)
        self.text_set_signal.connect(self._set_text)
        self.error_signal.connect(self._show_error_dialog)
        
        self.voice_finished_signal.connect(self.voice_finished)
        
        # Initialize audio engine
        try:
            self.audio_engine = AudioEngine()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Voice",
                f"Voice engine unavailable:\n\n{e}"
            )
            self.audio_engine = None
        self.voice_profile = VoiceProfile()
        self.current_state = VoiceState.IDLE
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_duration = 0
        
        # Setup UI
        self.setup_ui()
        self.connect_signals()
        self.load_settings()
        
        # Apply dark theme
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== Header =====
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("🎤 Buster Voice")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("● Ready")
        self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)
        
        # Device info
        self.device_label = QLabel("🎙️ Default")
        self.device_label.setStyleSheet("color: #569cd6; font-weight: bold;")
        header_layout.addWidget(self.device_label)
        
        layout.addWidget(header_widget)
        
        # ===== Main Content =====
        content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(content_splitter, 1)
        
        # Audio visualizer
        self.visualizer = AudioVisualizer()
        self.visualizer.setMinimumHeight(200)
        content_splitter.addWidget(self.visualizer)
        
        # Bottom section with controls and info
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(8)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Recording controls
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
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                background:#444;
                min-width:1px;
                max-width:1px;
            }
        """)
        record_layout.addWidget(separator)
        
        
        # Recording timer
        self.recording_time_label = QLabel("00:00")
        self.recording_time_label.setStyleSheet("""
            color: #f44747;
            font-size: 14pt;
            font-weight: bold;
            font-family: 'Consolas', monospace;
        """)
        record_layout.addWidget(self.recording_time_label)
        
        record_layout.addStretch()
        
        # Voice controls
        self.tts_btn = QPushButton("🔊 Speak")
        self.tts_btn.setStyleSheet(self.get_button_style("#4ec9b0"))
        self.tts_btn.clicked.connect(self.speak_text)
        record_layout.addWidget(self.tts_btn)
        
        self.stt_btn = QPushButton("📝 Transcribe")
        self.stt_btn.setStyleSheet(self.get_button_style("#569cd6"))
        self.stt_btn.clicked.connect(self.transcribe_audio)
        record_layout.addWidget(self.stt_btn)
        
        bottom_layout.addLayout(record_layout)
        
        # Text input area
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
            QTextEdit:focus {
                border-color: #4ec9b0;
            }
        """)
        text_layout.addWidget(self.text_input)
        
        bottom_layout.addWidget(text_widget)
        
        # Info and settings
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Info display
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
        
        # Settings panel
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(2)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # Speed control
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
        
        # Volume control
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
        
        # Visualization mode
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
        
        # Status bar
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
        
        # Recording quality indicator
        self.quality_label = QLabel("🎙️ High Quality")
        status_bar.addPermanentWidget(self.quality_label)
        
        status_bar.addPermanentWidget(QLabel("✨ Voice v1.0"))
        layout.addWidget(status_bar)
        
    def connect_signals(self):
        if not self.audio_engine:
            return

        self.audio_engine.audio_data_ready.connect(
            self.visualizer.update_data
        )

        self.audio_engine.recording_finished.connect(
            self.on_recording_finished
        )

        self.audio_engine.status_changed.connect(
            self.update_status
        )

        self.audio_engine.error_occurred.connect(
            self.show_error
        )
    
    def apply_dark_theme(self):
        """Apply dark theme to the widget"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI', 'Consolas', monospace;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #555555;
            }
            QSlider::groove:horizontal {
                background-color: #333333;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background-color: #4ec9b0;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #5ed9c0;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox:hover {
                border-color: #4ec9b0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                selection-background-color: #3d3d3d;
            }
            QSplitter::handle {
                background-color: #333333;
            }
            QSplitter::handle:hover {
                background-color: #4ec9b0;
            }
        """)
    
    def get_button_style(self, color: str) -> str:
        """Get style for colored buttons"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: #1e1e1e;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {color}cc;
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
            }}
        """
    
    @Slot()
    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.current_state == VoiceState.IDLE:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording audio"""
        if not PYAUDIO_AVAILABLE:
            self.show_error(
                "PyAudio is not installed.\n\nInstall with:\n\npip install pyaudio"
            )
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
        
        self.update_status("Recording...")
        self.info_text.append("🎙️ Recording started...")
    
    @Slot()
    def stop_recording(self):
        """Stop recording audio"""
        if self.audio_engine:
            self.audio_engine.stop_recording()

        self.current_state = VoiceState.IDLE
        self.record_btn.setText("🔴 Record")
        self.record_btn.setStyleSheet(self.get_button_style("#f44747"))
        self.stop_btn.setEnabled(False)
        self.recording_timer.stop()
        self.recording_time_label.setText("00:00")

        self.update_status("Recording stopped")
        self.info_text.append("⏹ Recording stopped")
        
    def on_recording_finished(self, filename: str):
        """Handle recording finished"""
        self.info_text.append(f"💾 Recording saved: {os.path.basename(filename)}")
        self.update_status(f"Recording saved: {os.path.basename(filename)}")
        
        # Auto-transcribe if enabled
        if hasattr(self, 'auto_transcribe') and self.auto_transcribe.isChecked():
            self.transcribe_audio(filename)
    
    @Slot()
    def update_recording_time(self):
        """Update recording timer display"""
        self.recording_duration += 1
        minutes = self.recording_duration // 60
        seconds = self.recording_duration % 60
        self.recording_time_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    @Slot()
    def speak_text(self):
        """Speak the text from input"""
        text = self.text_input.toPlainText().strip()
        if not text:
            text = self.info_text.toPlainText().strip()
            if not text:
                self.show_error("No text to speak")
                return
        
        self.tts_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.stt_btn.setEnabled(False)
        self.current_state = VoiceState.PLAYING
        self.update_status("Speaking...")
        
        # Run TTS in background
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()
    
    def _speak_thread(self, text):
        # FIXED: Thread-safe GUI updates using signals
        if not self.audio_engine:
            self.error_signal.emit("Voice engine unavailable.")
            return

        try:
            self.audio_engine.synthesize_speech(
                text,
                self.voice_profile
            )

            self.current_state = VoiceState.IDLE
            
            # FIXED: Use signals instead of direct GUI calls
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
    
    @Slot()
    def transcribe_audio(self, audio_file: str = None):
        """Transcribe audio to text"""
        self.current_state = VoiceState.PROCESSING
        self.update_status("Transcribing...")
        
        # Run STT in background
        threading.Thread(target=self._transcribe_thread, args=(audio_file,), daemon=True).start()
    
    def _transcribe_thread(self, audio_file: str = None):
        """Background thread for STT - FIXED with thread-safe GUI updates"""
        if not self.audio_engine:
            self.error_signal.emit("Voice engine unavailable.")
            return
            
        try:
            # Get latest recording if no file specified
            if not audio_file:
                recordings = list(self.audio_engine.recording_path.glob("*.wav"))
                if recordings:
                    audio_file = str(sorted(recordings)[-1])
                else:
                    self.error_signal.emit("No audio file to transcribe")
                    return
            
            text = self.audio_engine.recognize_speech(audio_file)
            if text:
                # FIXED: Use signals instead of direct GUI calls
                self.text_set_signal.emit(text)
                self.info_append_signal.emit(f"📝 Transcribed: {text[:100]}...")
                self.status_update_signal.emit("Transcription complete")
            else:
                self.error_signal.emit("No speech recognized")
            
            self.current_state = VoiceState.IDLE
            self.status_update_signal.emit("Ready")
            
        except Exception as e:
            self.error_signal.emit(f"Transcription error: {str(e)}")
            self.current_state = VoiceState.IDLE
    
    @Slot()
    def update_voice_settings(self):
        """Update voice settings from sliders"""
        speed = self.speed_slider.value()
        volume = self.volume_slider.value()
        
        self.speed_label.setText(str(speed))
        self.volume_label.setText(f"{volume}%")
        
        self.voice_profile.rate = speed
        self.voice_profile.volume = volume / 100.0
        
        self.update_status(f"Settings updated: {speed} WPM, {volume}% volume")
    
    @Slot(str)
    def change_visualization_mode(self, mode: str):
        """Change the visualization mode"""
        mode_map = {
            "Waveform": "waveform",
            "Spectrum": "spectrum",
            "Spectrogram": "spectrogram"
        }
        self.visualizer.set_mode(mode_map.get(mode, "waveform"))
        self.update_status(f"Visualization mode: {mode}")
    
    @Slot(str)
    def update_status(self, status: str):
        """Update status display"""
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
    
    # FIXED: Added slot for thread-safe info append
    @Slot(str)
    def _append_info(self, text: str):
        """Append text to info display (thread-safe)"""
        self.info_text.append(text)
    
    # FIXED: Added slot for thread-safe text setting
    @Slot(str)
    def _set_text(self, text: str):
        """Set text input content (thread-safe)"""
        self.text_input.setText(text)
    
    # FIXED: Added slot for thread-safe error dialog
    @Slot(str)
    def _show_error_dialog(self, error: str):
        """Show error dialog (thread-safe)"""
        QMessageBox.warning(self, "Voice Error", error)
    
    @Slot(str)
    def show_error(self, error: str):
        self.info_text.append(f"❌ Error: {error}")
        self.update_status(f"Error: {error}")
        self.status_indicator.setText("● Error")
        self.status_indicator.setStyleSheet(
            "color:#f44747;font-weight:bold;"
        )
        self.current_state = VoiceState.ERROR

        self._show_error_dialog(error)
    
    def load_settings(self):
        """Load saved settings"""
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
        """Save current settings"""
        settings = {
            'speed': self.speed_slider.value(),
            'volume': self.volume_slider.value(),
        }
        
        try:
            with open("voice_settings.json", 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_settings()
        self.recording_timer.stop()
        if self.audio_engine:
            self.audio_engine.stop_recording()
            self.audio_engine.quit()
            self.audio_engine.wait()
        event.accept()