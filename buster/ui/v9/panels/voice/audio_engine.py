"""
audio_engine.py - Background Audio Engine Thread
Handles recording, wave saving, TTS synthesis, and speech recognition.
"""

import os
import wave
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from enum import Enum

from PySide6.QtCore import QThread, Signal, QMutex

# Optional Library Handling
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


class AudioEngine(QThread):
    """Background thread for audio processing"""

    audio_data_ready = Signal(np.ndarray)
    recording_finished = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, recording_path: str | Path = "recordings"):
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

        # TTS Engine setup
        self.tts_engine = None
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.setup_tts()
            except Exception as e:
                print(f"[AudioEngine] TTS Init warning: {e}")

        # Speech Recognizer setup
        self.recognizer = None
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()

        self.recording_path = Path(recording_path).expanduser().resolve()
        self.recording_path.mkdir(exist_ok=True)

        self.visualization_data = np.zeros(1024)
        self.fft_data = np.zeros(512)

    def setup_tts(self):
        """Setup TTS engine parameters"""
        if self.tts_engine:
            try:
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    self.tts_engine.setProperty('voice', voices[0].id)
                self.tts_engine.setProperty('rate', 180)
                self.tts_engine.setProperty('volume', 0.8)
            except Exception as e:
                print(f"[AudioEngine] TTS Property set failed: {e}")

    def start_recording(self):
        """Start audio stream recording"""
        if not PYAUDIO_AVAILABLE or self.p is None:
            self.error_occurred.emit("PyAudio is not available on this system.")
            return

        self.mutex.lock()
        try:
            if self.is_recording:
                return

            self.audio_data = []
            self.is_recording = True

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
        """Stop audio stream recording"""
        self.mutex.lock()
        try:
            if not self.is_recording:
                return

            self.is_recording = False

            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

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
        """Callback processing raw input frames"""
        if self.is_recording:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            self.audio_data.append(audio_data)

            if len(audio_data) >= 1024:
                self.visualization_data = audio_data[:1024]
            else:
                self.visualization_data = np.pad(audio_data, (0, 1024 - len(audio_data)))

            self.fft_data = np.abs(np.fft.fft(self.visualization_data))[:512]
            self.audio_data_ready.emit(self.visualization_data)

        if PYAUDIO_AVAILABLE:
            return (in_data, pyaudio.paContinue)
        return (None, 0)

    def _save_wave(self, filename: str, audio_data: List[np.ndarray]):
        """Save captured PCM frames into standard WAV format"""
        try:
            audio_bytes = b''.join([data.tobytes() for data in audio_data])

            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)

                if self.p is None or self.format is None:
                    self.error_occurred.emit("Audio device unavailable.")
                    return

                wf.setsampwidth(self.p.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_bytes)

        except Exception as e:
            self.error_occurred.emit(f"Error saving wave file: {str(e)}")

    def synthesize_speech(self, text: str, voice_profile: VoiceProfile = None):
        """Synthesize text into vocal output"""
        if not TTS_AVAILABLE or not self.tts_engine:
            self.error_occurred.emit("TTS engine not available")
            return

        try:
            self.status_changed.emit("Synthesizing speech...")

            if voice_profile:
                self.tts_engine.setProperty('rate', voice_profile.rate)
                self.tts_engine.setProperty('volume', voice_profile.volume)

            self.tts_engine.say(text)
            self.tts_engine.runAndWait()

            self.status_changed.emit("Speech synthesis complete")

        except Exception as e:
            self.error_occurred.emit(f"Error synthesizing speech: {str(e)}")

    def recognize_speech(self, audio_file: str = None) -> str:
        """Recognize spoken text from WAV file or microphone"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.error_occurred.emit("Speech recognition not available")
            return ""

        try:
            self.status_changed.emit("Recognizing speech...")

            if audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio = self.recognizer.record(source)
            else:
                with sr.Microphone() as source:
                    self.status_changed.emit("Listening...")
                    audio = self.recognizer.listen(source)

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
        """Background loop"""
        while not self.isInterruptionRequested():
            self.msleep(100)

    def __del__(self):
        if self.stream:
            try:
                self.stream.close()
            except Exception:
                pass
        if self.p:
            try:
                self.p.terminate()
            except Exception:
                pass