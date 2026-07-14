from __future__ import annotations
from typing import Dict, Any, List
from .observation import VisualObservation
from .memory import VisualMemory
from .patterns import VisualPatternEngine

class VisualLearner:
    def __init__(self, data_dir: str = "data") -> None: self.memory = VisualMemory(data_dir); self.patterns = VisualPatternEngine()
    def observe(self, label: str, confidence: float = 0.0, context: str = "", source: str = "camera", details: Dict[str, Any] | None = None) -> Dict[str, Any]:
        obs = VisualObservation(label=label, confidence=confidence, context=context, source=source, details=details or {}).to_dict(); self.memory.add_observation(obs); return obs
    def learn_patterns(self) -> List[Dict[str, Any]]:
        data = self.memory.load(); patterns = self.patterns.discover_patterns(data.get("observations", []))
        for p in patterns: self.memory.add_pattern(p)
        return patterns
    def summarize(self) -> Dict[str, Any]:
        data = self.memory.load(); return {"observations": len(data.get("observations", [])), "patterns": len(data.get("patterns", [])), "updated": data.get("updated")}
