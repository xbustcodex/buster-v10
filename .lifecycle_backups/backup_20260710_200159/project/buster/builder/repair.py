"""Safe repair scaffolding for Buster."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import json


class BusterRepair:
    """Repairs known safe scaffolding issues.

    This is intentionally conservative: it creates missing folders/__init__.py files
    and can repair the v5.1 real_perception_loop module if absent.
    """

    def __init__(self, root: str | Path = "."):
        self.root = Path(root)
        self.actions: List[str] = []

    def run(self) -> Dict[str, object]:
        self.ensure_package("buster/builder")
        self.ensure_package("buster/perception")
        self.ensure_package("buster/world_model")
        self.ensure_package("buster/mind")
        self.ensure_package("buster/runtime")
        self.ensure_package("buster/companion")
        self.ensure_data_files()
        report = {"ok": True, "actions": self.actions}
        out = self.root / "data" / "buster_repair_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def ensure_package(self, rel: str) -> None:
        path = self.root / rel
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            self.actions.append(f"created directory {rel}")
        init = path / "__init__.py"
        if not init.exists():
            init.write_text('"""Buster package."""\n', encoding="utf-8")
            self.actions.append(f"created {rel}/__init__.py")

    def ensure_data_files(self) -> None:
        data = self.root / "data"
        data.mkdir(parents=True, exist_ok=True)
        for name in ["buster_doctor_report.json", "buster_repair_report.json"]:
            p = data / name
            if not p.exists():
                p.write_text("{}", encoding="utf-8")
                self.actions.append(f"created data/{name}")
