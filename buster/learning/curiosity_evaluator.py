from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CuriosityTarget:
    target_path: str
    score: float
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CuriosityEvaluator:
    """Evaluates codebase files/modules and calculates curiosity scores for exploration targets."""

    def __init__(
        self,
        project_root: str | Path = ".",
        target_extensions: Optional[List[str]] = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.target_extensions = target_extensions or [".py"]

    def evaluate_file(self, file_path: str | Path, context: Optional[Dict[str, Any]] = None) -> CuriosityTarget:
        path = Path(file_path).resolve()
        reasons: List[str] = []
        score = 0.0
        context = context or {}

        if not path.exists() or not path.is_file():
            return CuriosityTarget(
                target_path=str(file_path),
                score=0.0,
                reasons=["File does not exist or is not a regular file"],
            )

        # 1. Age / Staleness Metric (Max +30)
        try:
            mtime = path.stat().st_mtime
            age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400.0
            if age_days > 7:
                staleness_score = min(30.0, age_days * 2.0)
                score += staleness_score
                reasons.append(f"File has not been modified in {int(age_days)} days (+{staleness_score:.1f})")
        except Exception:
            pass

        # 2. DLQ / Failure History Metric (Max +40)
        failure_count = context.get("failure_counts", {}).get(str(path), 0)
        if failure_count > 0:
            failure_score = min(40.0, failure_count * 15.0)
            score += failure_score
            reasons.append(f"Associated with {failure_count} past execution failures (+{failure_score:.1f})")

        # 3. Code Complexity / Size Metric (Max +30)
        try:
            lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
            if lines > 150:
                complexity_score = min(30.0, (lines - 150) * 0.1)
                score += complexity_score
                reasons.append(f"High file complexity ({lines} lines) (+{complexity_score:.1f})")
        except Exception:
            pass

        return CuriosityTarget(
            target_path=str(path.relative_to(self.project_root) if path.is_relative_to(self.project_root) else path),
            score=round(score, 2),
            reasons=reasons,
            metadata={"lines": lines if 'lines' in locals() else 0},
        )

    def scan_project(self, limit: int = 10, context: Optional[Dict[str, Any]] = None) -> List[CuriosityTarget]:
        """Scans the project directory and returns ranked curiosity targets."""
        targets: List[CuriosityTarget] = []

        for root, _, files in os.walk(self.project_root):
            # Skip hidden and cache folders
            if any(part.startswith(".") or part in ("__pycache__", "venv", "env", "node_modules") for part in Path(root).parts):
                continue

            for file in files:
                if any(file.endswith(ext) for ext in self.target_extensions):
                    full_path = Path(root) / file
                    target = self.evaluate_file(full_path, context=context)
                    # Include targets with score >= 0 instead of strict > 0
                    if target.score >= 0:
                        targets.append(target)

        targets.sort(key=lambda x: x.score, reverse=True)
        return targets[:limit]