from __future__ import annotations

import platform
from typing import Any, Dict, List, Optional


class AttentionSystem:
    """Hardware, Kernel & Cognitive-Aware Multi-Modal Attention Allocator."""

    def __init__(self) -> None:
        self.hardware_profile = {
            "processor": platform.processor() or platform.machine(),
            "kernel": platform.release(),
            "system": platform.system(),
        }

    def choose_focus(
        self,
        observations: List[Dict[str, Any]],
        system_load: float = 0.0,
        current_life_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not observations:
            return {
                "focus": "idle",
                "reason": "No observations",
                "importance": 0.0,
                "hardware": self.hardware_profile,
            }

        def _calculate_boosted_importance(obs: Dict[str, Any]) -> float:
            base_importance = float(obs.get("importance", 0.0))
            source = str(obs.get("source", "")).lower()
            text = str(obs.get("text", "") or obs.get("summary", "")).lower()

            # Priority Boost 1: Wake word activation
            if "buster" in text:
                base_importance += 0.4

            # Priority Boost 2: Hardware/Kernel failure signals
            if any(k in text for k in ["kernel", "error", "traceback", "cpu_spike", "memory_leak", "hardware"]):
                base_importance += 0.35

            # Priority Boost 3: Screen/IDE terminal execution context
            if source == "screen" and any(k in text for k in ["pytest", "python", "termux", "terminal"]):
                base_importance += 0.2

            return min(1.0, max(0.0, base_importance))

        ranked = sorted(observations, key=_calculate_boosted_importance, reverse=True)
        top = ranked[0]
        top_importance = _calculate_boosted_importance(top)

        focus = top.get("sound_type") or top.get("scene") or top.get("source", "unknown")
        
        # Determine explicit focus reason
        top_text = str(top.get("text", "") or top.get("summary", "")).lower()
        if "buster" in top_text:
            reason = "Wake word detected"
        elif any(k in top_text for k in ["kernel", "error", "traceback"]):
            reason = "Kernel/Hardware alert or error detected"
        else:
            reason = "Highest priority multi-modal perception event"

        return {
            "focus": focus,
            "reason": reason,
            "importance": top_importance,
            "observation": top,
            "hardware": self.hardware_profile,
            "system_load": system_load,
            "life_state": current_life_state or "WORK",
        }