from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MilestoneSummary:
    timestamp: str
    patches_applied: List[Dict[str, Any]] = field(default_factory=list)
    curiosity_tasks_completed: List[Dict[str, Any]] = field(default_factory=list)
    dreams_executed: int = 0
    failures_logged: int = 0


class MilestoneReporter:
    """Generates daily morning summary logs detailing overnight auto-fixes, patches, and curiosity explorations."""

    def __init__(self, log_dir: str | Path = "data/milestones") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        patches: Optional[List[Dict[str, Any]]] = None,
        explorations: Optional[List[Dict[str, Any]]] = None,
        dreams_count: int = 0,
        failures_count: int = 0,
    ) -> MilestoneSummary:
        now_iso = datetime.now(timezone.utc).isoformat()
        summary = MilestoneSummary(
            timestamp=now_iso,
            patches_applied=patches or [],
            curiosity_tasks_completed=explorations or [],
            dreams_executed=dreams_count,
            failures_logged=failures_count,
        )

        filename = f"milestone_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        target_path = self.log_dir / filename
        target_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

        formatted_console = self.format_console_log(summary)
        logger.info(f"\n{formatted_console}")
        return summary

    def format_console_log(self, summary: MilestoneSummary) -> str:
        lines = [
            "==================================================",
            "          🌅 MORNING MILESTONE REPORT             ",
            "==================================================",
            f"Timestamp: {summary.timestamp}",
            f"• Overnight Dreams Executed: {summary.dreams_executed}",
            f"• Code Patches Applied: {len(summary.patches_applied)}",
            f"• Curiosity Explorations: {len(summary.curiosity_tasks_completed)}",
            f"• Unresolved Failures Logged: {summary.failures_logged}",
        ]

        if summary.patches_applied:
            lines.append("\n--- Patches Applied ---")
            for p in summary.patches_applied:
                lines.append(f"  - [{p.get('hurdle_id', 'N/A')}] {p.get('target_file', 'unknown')}: {p.get('summary', 'No summary')}")

        if summary.curiosity_tasks_completed:
            lines.append("\n--- Curiosity Explorations ---")
            for c in summary.curiosity_tasks_completed:
                lines.append(f"  - Path: {c.get('target_path', 'unknown')} | Score: {c.get('curiosity_score', 0.0)}")

        lines.append("==================================================")
        return "\n".join(lines)