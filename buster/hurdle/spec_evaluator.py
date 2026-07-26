# buster/hurdle/spec_evaluator.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from buster.cognitive.strategic_planner import StrategicPlanner, RoadmapSpecification

logger = logging.getLogger(__name__)


class AutonomousSpecEvaluator:
    """Evaluates growth ledgers, hurdle logs, and hardware telemetry to trigger self-directed upgrade specs."""

    def __init__(
        self,
        growth_ledger_path: str | Path = "data/growth_ledger.json",
        strategic_planner: Optional[StrategicPlanner] = None,
    ) -> None:
        self.growth_ledger_path = Path(growth_ledger_path)
        self.planner = strategic_planner or StrategicPlanner()

    def evaluate_and_propose_spec(self, target_phase: str = "Phase 25") -> Optional[RoadmapSpecification]:
        """Scans growth logs for recurring hurdles and proposes a targeted upgrade specification."""
        hurdles = self._load_hurdles()
        if not hurdles:
            logger.info("No hurdles found in growth ledger. Upgrade spec evaluation skipped.")
            return None

        # Analyze recurring friction or error patterns
        error_counts: Dict[str, int] = {}
        for h in hurdles:
            msg = h.get("error_message") or h.get("hurdle", "unknown")
            error_counts[msg] = error_counts.get(msg, 0) + 1

        # Sort by frequency
        sorted_friction = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        top_issue, frequency = sorted_friction[0]

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        spec_id = f"auto_upgrade_{target_phase.lower()}_{now_str}"
        title = f"Autonomous Remediation & Enhancement for: {top_issue[:40]}"
        
        objectives = [
            f"Address recurring runtime friction (Frequency: {frequency})",
            f"Root cause: {top_issue}",
            "Implement automated self-healing wrapper and patch validation",
        ]

        spec = self.planner.generate_spec(
            spec_id=spec_id,
            title=title,
            target_phase=target_phase,
            objectives=objectives,
            hardware_deps=["processor", "memory", "kernel"],
        )

        logger.info(f"Autonomous Spec Evaluator generated specification: {spec_id}")
        return spec

    def _load_hurdles(self) -> List[Dict[str, Any]]:
        if not self.growth_ledger_path.exists():
            return []
        try:
            raw = json.loads(self.growth_ledger_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw.get("hurdles", [])
            elif isinstance(raw, list):
                return raw
        except Exception as e:
            logger.error(f"Failed to load growth ledger for spec evaluation: {e}")
        return []