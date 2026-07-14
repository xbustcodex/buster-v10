from pathlib import Path
import json
import textwrap
from datetime import datetime, timezone

ROOT = Path.cwd()

FILES = {}

FILES['buster/perception/real_perception_loop.py'] = r'''
"""Real perception loop for Buster.

This module repairs the missing v5.1 import and provides a lightweight
integration loop that can accept camera/screen/audio/project observations,
normalize them, and optionally forward them into the World Model and Mind.
It is intentionally dependency-light so tests and startup do not require
camera or microphone hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json
import uuid

DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "real_perception_loop_state.json"
OBS_FILE = DATA_DIR / "real_perception_loop_observations.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@dataclass
class PerceptionObservation:
    source: str
    kind: str
    summary: str
    confidence: float = 0.5
    importance: float = 0.5
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RealPerceptionLoop:
    """Lightweight real perception loop.

    The loop does not force hardware access. Instead, external camera,
    microphone, screen, or project watchers can feed observations into it.
    This keeps tests stable while still giving Buster a real integration point.
    """

    def __init__(self, data_dir: str | Path = "data", auto_persist: bool = True):
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "real_perception_loop_state.json"
        self.observations_file = self.data_dir / "real_perception_loop_observations.json"
        self.auto_persist = auto_persist
        self.running = False
        self.tick_count = 0
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self.state: Dict[str, Any] = _load_json(self.state_file, {
            "running": False,
            "tick_count": 0,
            "last_tick": None,
            "last_observation": None,
            "sources": {},
        })
        self.observations: List[Dict[str, Any]] = _load_json(self.observations_file, [])

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.state["running"] = True
        self.state["started_at"] = _now()
        self._persist()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.state["running"] = False
        self.state["stopped_at"] = _now()
        self._persist()
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "running": bool(self.running or self.state.get("running")),
            "tick_count": int(self.state.get("tick_count", self.tick_count)),
            "observations": len(self.observations),
            "last_tick": self.state.get("last_tick"),
            "last_observation": self.state.get("last_observation"),
            "sources": self.state.get("sources", {}),
        }

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.subscribers.append(callback)

    def observe(self, source: str, kind: str, summary: str, confidence: float = 0.5,
                importance: float = 0.5, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        obs = PerceptionObservation(
            source=source,
            kind=kind,
            summary=summary,
            confidence=max(0.0, min(1.0, float(confidence))),
            importance=max(0.0, min(1.0, float(importance))),
            data=data or {},
        ).to_dict()
        self.observations.append(obs)
        self.state["last_observation"] = obs
        sources = self.state.setdefault("sources", {})
        src = sources.setdefault(source, {"count": 0, "last_seen": None})
        src["count"] += 1
        src["last_seen"] = obs["timestamp"]
        self._notify(obs)
        self._persist()
        return obs

    def tick(self) -> Dict[str, Any]:
        self.tick_count = int(self.state.get("tick_count", 0)) + 1
        self.state["tick_count"] = self.tick_count
        self.state["last_tick"] = _now()
        result = {
            "tick": self.tick_count,
            "timestamp": self.state["last_tick"],
            "running": self.running,
            "observations": len(self.observations),
        }
        self._persist()
        return result

    def drain_recent(self, limit: int = 25) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        return self.observations[-limit:]

    def clear(self) -> None:
        self.observations = []
        self.state["last_observation"] = None
        self._persist()

    def _notify(self, observation: Dict[str, Any]) -> None:
        for callback in list(self.subscribers):
            try:
                callback(observation)
            except Exception:
                # Perception should not crash because a subscriber failed.
                continue

    def _persist(self) -> None:
        if not self.auto_persist:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        self.observations_file.write_text(json.dumps(self.observations[-500:], indent=2), encoding="utf-8")


__all__ = ["PerceptionObservation", "RealPerceptionLoop"]
'''

FILES['buster/builder/__init__.py'] = r'''
"""Buster self-maintenance builder package."""
from .doctor import BusterDoctor
from .repair import BusterRepair

__all__ = ["BusterDoctor", "BusterRepair"]
'''

FILES['buster/builder/storage.py'] = r'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def save_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
'''

FILES['buster/builder/doctor.py'] = r'''
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
'''

FILES['buster/builder/repair.py'] = r'''
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
'''

FILES['buster/builder/cli.py'] = r'''
from __future__ import annotations

import argparse
import json
from .doctor import BusterDoctor
from .repair import BusterRepair


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="buster-builder", description="Buster self-maintenance tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check project health")
    sub.add_parser("repair", help="Apply safe repairs")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        result = BusterDoctor().run()
    elif args.command == "repair":
        result = BusterRepair().run()
    else:
        parser.error("unknown command")
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

FILES['test_v6_0_buster_builder_doctor.py'] = r'''
from buster.builder.doctor import BusterDoctor
from buster.builder.repair import BusterRepair
from buster.perception.real_perception_loop import RealPerceptionLoop


def test_real_perception_loop_basic():
    loop = RealPerceptionLoop(auto_persist=False)
    status = loop.start()
    assert status["running"] is True
    obs = loop.observe("camera", "object", "desk visible", confidence=0.9, importance=0.6)
    assert obs["source"] == "camera"
    assert loop.tick()["tick"] >= 1
    assert len(loop.drain_recent()) == 1
    loop.stop()


def test_buster_doctor_and_repair():
    repair = BusterRepair()
    repair_report = repair.run()
    assert repair_report["ok"] is True
    doctor = BusterDoctor()
    report = doctor.run()
    assert "issues" in report
    assert isinstance(report["issue_count"], int)
'''

FILES['apply_fix_v5_1_and_v6_0_buster_builder.py'] = None


def write_file(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding='utf-8')
    print(f"[WRITE] {rel}")


def ensure_json(rel: str, default):
    path = ROOT / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding='utf-8')
        print(f"[CREATE] {rel}")
    else:
        print(f"[SKIP] {rel}")


def main():
    print("=== Applying Buster v5.1 Fix + v6.0 Builder Doctor Foundation ===")
    for rel, content in FILES.items():
        if rel == 'apply_fix_v5_1_and_v6_0_buster_builder.py':
            continue
        write_file(rel, content)
    ensure_json('data/real_perception_loop_state.json', {"running": False, "tick_count": 0, "last_tick": None, "sources": {}})
    ensure_json('data/real_perception_loop_observations.json', [])
    ensure_json('data/buster_doctor_report.json', {})
    ensure_json('data/buster_repair_report.json', {})
    print("\nSUCCESS: Missing v5.1 module repaired and v6.0 Buster Builder Doctor installed.")
    print("Next: python -m pytest")

if __name__ == '__main__':
    main()
