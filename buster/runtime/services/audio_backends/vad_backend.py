from __future__ import annotations
import wave
from pathlib import Path
import numpy as np

class VADBackend:
    def __init__(self, aggressiveness=2, rms_threshold=350.0):
        self.aggressiveness = max(0, min(3, int(aggressiveness)))
        self.rms_threshold = float(rms_threshold)
        self._webrtcvad = None
        try:
            import webrtcvad
            self._webrtcvad = webrtcvad.Vad(self.aggressiveness)
        except ImportError:
            pass

    @property
    def available(self):
        return True

    @property
    def backend(self):
        return "webrtcvad" if self._webrtcvad is not None else "rms"

    def status(self):
        return {
            "status": "ready",
            "available": True,
            "configured": True,
            "backend": self.backend,
        }

    def has_speech(self, audio_file):
        path = Path(audio_file).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)

        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())

        if sample_width != 2:
            return True

        samples = np.frombuffer(frames, dtype=np.int16)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)

        if self._webrtcvad is not None and sample_rate in {8000, 16000, 32000, 48000}:
            frame_ms = 30
            frame_size = int(sample_rate * frame_ms / 1000)
            speech_frames = 0
            total_frames = 0
            for start in range(0, len(samples) - frame_size + 1, frame_size):
                total_frames += 1
                frame = samples[start:start + frame_size].tobytes()
                if self._webrtcvad.is_speech(frame, sample_rate):
                    speech_frames += 1
            if total_frames:
                return speech_frames / total_frames >= 0.08

        if samples.size == 0:
            return False

        rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        return rms >= self.rms_threshold
