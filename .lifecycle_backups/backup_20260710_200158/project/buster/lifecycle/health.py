import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import HealthReport


class HealthManager:
    def __init__(self, root: Path):
        self.root = Path(root)

    def check(self) -> dict:
        issues = []
        warnings = []
        recommendations = []

        runtime_score = 100
        imports_score = 100
        config_score = 100
        plugins_score = 100
        database_score = 100

        required = [
            "buster",
            "buster/lifecycle",
            "version.json",
            "config/lifecycle_config.json"
        ]

        for rel in required:
            if not (self.root / rel).exists():
                issues.append(f"Missing required path: {rel}")

        try:
            import requests
            import packaging
        except Exception as e:
            imports_score = 60
            warnings.append(f"Optional dependency issue: {e}")
            recommendations.append("Run: pip install requests packaging colorama pyyaml")

        if issues:
            runtime_score = 60

        scores = [runtime_score, imports_score, config_score, plugins_score, database_score]
        overall = sum(scores) / len(scores)

        report = HealthReport(
            overall_score=overall,
            runtime_score=runtime_score,
            imports_score=imports_score,
            config_score=config_score,
            plugins_score=plugins_score,
            database_score=database_score,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

        return asdict(report)

    def save(self, report: dict):
        path = self.root / "data" / "lifecycle_health.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=4), encoding="utf-8")
