"""Project health checks for Buster itself."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List
import importlib.util
import json


@dataclass
class DoctorIssue:
    code: str
    severity: str
    message: str
    target: str
    fixable: bool = False

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class BusterDoctor:
    """Checks Buster for missing modules, broken imports, and required folders."""

    REQUIRED_MODULES = [
        "buster.perception.real_perception_loop",
        "buster.runtime.engine",
        "buster.world_model.engine",
        "buster.mind.engine",
        "buster.companion.engine",
    ]

    REQUIRED_PATHS = [
        "buster/perception",
        "buster/world_model",
        "buster/mind",
        "buster/runtime",
        "buster/companion",
        "data",
    ]

    def __init__(self, root: str | Path = "."):
        self.root = Path(root)

    def run(self) -> Dict[str, object]:
        issues: List[DoctorIssue] = []
        for rel in self.REQUIRED_PATHS:
            path = self.root / rel
            if not path.exists():
                issues.append(DoctorIssue("missing_path", "error", f"Missing required path: {rel}", rel, True))

        for module in self.REQUIRED_MODULES:
            if importlib.util.find_spec(module) is None:
                rel = module.replace(".", "/") + ".py"
                issues.append(DoctorIssue("missing_module", "error", f"Missing module: {module}", rel, True))

        tests = sorted(self.root.glob("test_*.py"))
        if not tests:
            issues.append(DoctorIssue("missing_tests", "warning", "No root-level version tests found", "test_*.py", False))

        report = {
            "ok": not any(i.severity == "error" for i in issues),
            "issue_count": len(issues),
            "issues": [i.to_dict() for i in issues],
        }
        out = self.root / "data" / "buster_doctor_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
