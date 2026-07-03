from __future__ import annotations

from typing import Any, Dict

from buster.mind.storage import load_json, save_json, now_iso

WORLD_MIND_STATE = "data/world_model_mind_state.json"


class WorldModelMindBridge:
    """Summarizes the world model into cognitive context for the Mind layer."""

    def summarize_world(self) -> Dict[str, Any]:
        world = load_json("data/world_model.json", {})
        summary = {
            "timestamp": now_iso(),
            "entities": len(world.get("entities", [])) if isinstance(world, dict) else 0,
            "relationships": len(world.get("relationships", [])) if isinstance(world, dict) else 0,
            "observations": len(world.get("observations", [])) if isinstance(world, dict) else 0,
            "active_context": world.get("active_context", {}) if isinstance(world, dict) else {},
        }
        save_json(WORLD_MIND_STATE, summary)
        return summary
