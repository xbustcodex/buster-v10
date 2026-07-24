"""
Context Memory & State Persistence Engine for Buster v10.7
Manages short-term working memory, agent execution history, and long-term state persistence.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("buster.agents.memory")


class ContextMemory:
    """Thread-safe state memory and execution context store for agents."""

    def __init__(self, storage_dir: str = "data/memory") -> None:
        self.storage_path = Path(storage_dir)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._memory_file = self.storage_path / "global_context.json"

        self._lock = threading.RLock()
        self._working_memory: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

        self._load_state()

    def set_key(self, key: str, value: Any) -> None:
        """Stores a key-value pair in short-term working memory."""
        with self._lock:
            self._working_memory[key] = value
            self._save_state()

    def get_key(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieves a value from working memory."""
        with self._lock:
            return self._working_memory.get(key, default)

    def append_history(self, agent_id: str, action: str, result: Any) -> None:
        """Appends an agent action to the sequential context memory stream."""
        with self._lock:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "action": action,
                "result": result,
            }
            self._history.append(entry)
            self._save_state()

    def search_history(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Performs simple keyword search over recent execution context."""
        with self._lock:
            matches = []
            for item in reversed(self._history):
                if query.lower() in str(item).lower():
                    matches.append(item)
                    if len(matches) >= max_results:
                        break
            return matches

    def snapshot(self) -> Dict[str, Any]:
        """Returns full copy of current working memory and recent history."""
        with self._lock:
            return {
                "working_memory": self._working_memory.copy(),
                "history_count": len(self._history),
                "recent_history": self._history[-10:],
            }

    def _save_state(self) -> None:
        """Persists memory state to JSON file on disk."""
        try:
            data = {
                "working_memory": self._working_memory,
                "history": self._history[-500:],  # Retain last 500 actions
            }
            with open(self._memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to persist context memory state: {exc}")

    def _load_state(self) -> None:
        """Loads state from disk on startup if present."""
        if not self._memory_file.exists():
            return

        try:
            with open(self._memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._working_memory = data.get("working_memory", {})
                self._history = data.get("history", [])
            logger.info(f"Loaded memory state: {len(self._working_memory)} keys, {len(self._history)} history records.")
        except Exception as exc:
            logger.error(f"Failed to load context memory state: {exc}")