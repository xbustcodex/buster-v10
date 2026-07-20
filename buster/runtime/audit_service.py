"""
Buster Self-Improvement Audit Service v1.0

Provides lightweight, thread-safe, append-only JSON Lines persistent storage
for system audit records, decoupled from decision logic.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("buster.audit_service")


class AuditService:
    """Manages persistence and retrieval of safety layer audit events."""

    def __init__(self, storage_path: Optional[Union[str, Path]] = None) -> None:
        self.storage_path = (
            Path(storage_path).resolve()
            if storage_path
            else Path.cwd() / "audit_trail.jsonl"
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, audit_data: Union[Dict[str, Any], Any]) -> None:
        """
        Appends a new audit event to the JSON Lines storage file.
        Accepts raw dictionaries or objects with a `to_dict()` method.
        """
        payload = (
            audit_data.to_dict()
            if hasattr(audit_data, "to_dict")
            else dict(audit_data)
        )

        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as err:
            logger.error("Failed to write to audit trail: %s", err)

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Reads and returns the most recent audit events."""
        if not self.storage_path.exists():
            return []

        records: List[Dict[str, Any]] = []
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line.strip()))
        except Exception as err:
            logger.error("Failed to read audit history: %s", err)

        return records[-limit:]