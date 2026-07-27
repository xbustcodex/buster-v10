from __future__ import annotations
from pathlib import Path
from threading import Lock
from typing import Any

class WhisperBackend:
    def __init__(self, model_size="base", device="auto", compute_type="int8", language=None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Any = None
        self._backend = "unavailable"
        self._lock = Lock()
        self.last_error = ""

    @property
    def available(self):
        try:
            import faster_whisper  # noqa
            return True
        except ImportError:
            try:
                import whisper  # noqa
                return True
            except ImportError:
                return False

    @property
    def configured(self):
        return self.available

    def status(self):
        return {
            "status": "ready" if self.available else "not_installed",
            "available": self.available,
            "configured": self.configured,
            "backend": self._backend,
            "model": self.model_size,
            "device": self.device,
            "last_error": self.last_error,
        }

    def _load_model(self):
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from faster_whisper import WhisperModel
                device = self.device
                if device == "auto":
                    device = "cuda" if self._cuda_available() else "cpu"
                compute_type = self.compute_type
                if device == "cpu" and compute_type not in {"int8", "int8_float32", "float32"}:
                    compute_type = "int8"
                self._model = WhisperModel(
                    self.model_size,
                    device=device,
                    compute_type=compute_type,
                )
                self._backend = "faster-whisper"
                self.device = device
                return
            except ImportError:
                pass

            try:
                import whisper
                self._model = whisper.load_model(self.model_size)
                self._backend = "openai-whisper"
                self.device = "cuda" if self._cuda_available() else "cpu"
            except ImportError as exc:
                self.last_error = "Neither faster-whisper nor openai-whisper is installed."
                raise RuntimeError(self.last_error) from exc

    def preload(self) -> None:
        """Load the model before the first voice command."""
        self._load_model()

    def transcribe(
        self,
        audio_file,
        *,
        language=None,
        vad_filter=True,
        fast_mode=True,
    ):
        path = Path(audio_file).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        self._load_model()
        selected_language = self._normalize_language(
            language or self.language
        )

        if self._backend == "faster-whisper":
            options = {
                "language": selected_language,
                "vad_filter": vad_filter,
                "condition_on_previous_text": False,
                "without_timestamps": True,
            }
            if fast_mode:
                options.update(
                    {
                        "beam_size": 1,
                        "best_of": 1,
                        "temperature": 0.0,
                    }
                )
            else:
                options["beam_size"] = 5

            segments, info = self._model.transcribe(
                str(path),
                **options,
            )
            text_parts = []
            segment_list = []
            for segment in segments:
                text = str(segment.text).strip()
                if text:
                    text_parts.append(text)
                segment_list.append({
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": text,
                })
            return {
                "text": " ".join(text_parts).strip(),
                "language": getattr(info, "language", selected_language),
                "language_probability": getattr(info, "language_probability", None),
                "segments": segment_list,
                "backend": self._backend,
                "model": self.model_size,
            }

        result = self._model.transcribe(
            str(path),
            language=selected_language,
            fp16=self.device == "cuda",
            verbose=False,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        return {
            "text": str(result.get("text", "")).strip(),
            "language": result.get("language", selected_language),
            "segments": result.get("segments", []),
            "backend": self._backend,
            "model": self.model_size,
        }

    @staticmethod
    def _normalize_language(language):
        """
        Convert UI locale values into Whisper language codes.

        Examples:
            en-US -> en
            en_US -> en
            pt-BR -> pt
            zh-CN -> zh
        """
        if language is None:
            return None

        value = str(language).strip().lower()
        if not value or value in {"auto", "automatic", "detect"}:
            return None

        value = value.replace("_", "-")
        aliases = {
            "english": "en",
            "australian-english": "en",
            "american-english": "en",
            "british-english": "en",
            "chinese": "zh",
            "mandarin": "zh",
            "cantonese": "yue",
        }
        if value in aliases:
            return aliases[value]

        return value.split("-", 1)[0]

    @staticmethod
    def _cuda_available():
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False
