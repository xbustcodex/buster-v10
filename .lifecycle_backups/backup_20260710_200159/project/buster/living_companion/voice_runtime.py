from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

from buster.sdk import BusterSDK


class VoiceRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data", mode: str = "companion") -> None:
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.data_dir = Path(data_dir)
        self.mode = mode
        self.queue: List[Dict[str, Any]] = []
        self.spoken: List[Dict[str, Any]] = []
        self.state_file = self.data_dir / "living_voice_runtime_state.json"

    def enqueue(self, message: str, reason: str = "companion", priority: str = "normal") -> Dict[str, Any]:
        item = {"message": message, "reason": reason, "priority": priority}
        self.queue.append(item)
        self.sdk.publish("voice.queued", item, source="voice_runtime")
        self._persist()
        return item

    def speak_next(self) -> Dict[str, Any] | None:
        if not self.queue:
            return None
        item = self.queue.pop(0)
        self.spoken.append(item)
        self.sdk.speak(item["message"], reason=item["reason"])
        self._persist()
        return item

    def drain(self) -> List[Dict[str, Any]]:
        spoken = []
        while self.queue:
            item = self.speak_next()
            if item:
                spoken.append(item)
        return spoken

    def status(self) -> Dict[str, Any]:
        return {"mode": self.mode, "queued": self.queue, "spoken": self.spoken[-20:]}

    def _persist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")
