# buster/cognitive/strategic_planner.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RoadmapSpecification:
    spec_id: str
    title: str
    target_phase: str
    objectives: List[str]
    hardware_dependencies: List[str]
    status: str = "drafted"
    created_at: str = ""


class StrategicPlanner:
    """Synthesizes system telemetry and growth logs to generate autonomous architectural roadmaps."""

    def __init__(self, roadmap_dir: str | Path = "data/roadmaps") -> None:
        self.roadmap_dir = Path(roadmap_dir)
        self.roadmap_dir.mkdir(parents=True, exist_ok=True)

    def generate_spec(
        self,
        spec_id: str,
        title: str,
        target_phase: str,
        objectives: List[str],
        hardware_deps: Optional[List[str]] = None,
    ) -> RoadmapSpecification:
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        spec = RoadmapSpecification(
            spec_id=spec_id,
            title=title,
            target_phase=target_phase,
            objectives=objectives,
            hardware_dependencies=hardware_deps or ["cpu", "memory"],
            status="drafted",
            created_at=now_iso,
        )

        target_path = self.roadmap_dir / f"{spec_id}.json"
        target_path.write_text(json.dumps(asdict(spec), indent=2), encoding="utf-8")
        logger.info(f"Generated autonomous roadmap specification: {spec_id}")
        return spec