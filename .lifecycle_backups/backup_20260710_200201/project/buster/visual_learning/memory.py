from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

class VisualMemory:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir); self.data_dir.mkdir(parents=True, exist_ok=True); self.path = self.data_dir / "visual_learning_memory.json"
        if not self.path.exists(): self.path.write_text(json.dumps({"observations": [], "patterns": [], "updated": None}, indent=2), encoding="utf-8")
    def load(self) -> Dict[str, Any]:
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception: return {"observations": [], "patterns": [], "updated": None}
    def save(self, data: Dict[str, Any]) -> None: self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    def add_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        data = self.load(); data.setdefault("observations", []).append(observation); data["observations"] = data["observations"][-1000:]; data["updated"] = observation.get("timestamp"); self.save(data); return observation
    def add_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        data = self.load(); data.setdefault("patterns", []).append(pattern); data["patterns"] = data["patterns"][-500:]; data["updated"] = pattern.get("updated"); self.save(data); return pattern
