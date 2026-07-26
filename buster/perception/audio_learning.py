from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class AudioLearning:
    """Hardware & Runtime Aware Audio Phrase Learning System."""

    def __init__(self, storage_path: str | Path = "data/audio_learned_phrases.json") -> None:
        self.storage_path = Path(storage_path)
        self.phrases: Dict[str, Dict[str, Any]] = {}
        self.hardware_profile = {
            "processor": platform.processor() or platform.machine(),
            "kernel": platform.release(),
            "python_version": sys.version.split()[0],
        }
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.phrases = raw.get("phrases", {})
            except Exception:
                self.phrases = {}

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "phrases": self.phrases,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "hardware": self.hardware_profile,
        }
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def learn_phrase(
        self,
        phrase: str,
        meaning: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        key = phrase.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        entry = {
            "meaning": meaning,
            "learned_at": now_iso,
            "hardware": self.hardware_profile,
            "context": context or {},
        }
        self.phrases[key] = entry
        self._save()

        return {"phrase": key, "meaning": meaning, "learned": True, "entry": entry}

    def interpret(self, phrase: str) -> Optional[str]:
        key = phrase.strip().lower()
        val = self.phrases.get(key)
        if isinstance(val, dict):
            return val.get("meaning")
        return val