"""
Buster v3.6 Jarvis Autonomy Layer Patch

Adds:
- autonomy engine
- next-action recommender
- autonomous job/session records
- dashboard snapshot provider
- planner bridge that combines learning + plugins + autonomy

Run from your Buster project root:
    python apply_v3_6_jarvis_autonomy_layer.py
Then test:
    python test_v3_6_jarvis_autonomy_layer.py
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent


def write_file(relative_path: str, content: str) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")
    print(f"[WRITE] {relative_path}")


def write_json_if_missing(relative_path: str, default_data) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default_data, indent=2), encoding="utf-8")
        print(f"[CREATE] {relative_path}")
    else:
        print(f"[KEEP] {relative_path}")


FILES = {
    "buster/autonomy/__init__.py": '''
        """Buster Jarvis Autonomy Layer.

        This package lets Buster recommend next actions, remember autonomous
        sessions, and expose OS-style status snapshots to the dashboard.
        """

        from .engine import AutonomyEngine
        from .next_actions import NextActionRecommender
        from .records import AutonomyJob, AutonomyDecision
        from .dashboard import AutonomyDashboard

        __all__ = [
            "AutonomyEngine",
            "NextActionRecommender",
            "AutonomyJob",
            "AutonomyDecision",
            "AutonomyDashboard",
        ]
    ''',
    "buster/autonomy/records.py": '''
        from __future__ import annotations

        from dataclasses import dataclass, field, asdict
        from datetime import datetime
        from typing import Any, Dict, List
        import uuid


        def utc_now() -> str:
            return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


        @dataclass
        class AutonomyDecision:
            """A single planner decision made by the Jarvis autonomy layer."""

            request: str
            project_type: str = "general"
            recommended_action: str = "inspect"
            confidence: float = 0.5
            reason: str = "No reason recorded."
            strategy: str = "general"
            plugins: List[str] = field(default_factory=list)
            patterns: List[str] = field(default_factory=list)
            created_at: str = field(default_factory=utc_now)

            def to_dict(self) -> Dict[str, Any]:
                return asdict(self)

            @classmethod
            def from_dict(cls, data: Dict[str, Any]) -> "AutonomyDecision":
                allowed = cls.__dataclass_fields__.keys()
                return cls(**{k: v for k, v in data.items() if k in allowed})


        @dataclass
        class AutonomyJob:
            """One autonomous task/session record."""

            title: str
            request: str
            project: str = "default"
            project_type: str = "general"
            status: str = "queued"  # queued, running, completed, failed, paused
            assigned_agents: List[str] = field(default_factory=list)
            decision: Dict[str, Any] = field(default_factory=dict)
            result: Dict[str, Any] = field(default_factory=dict)
            job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
            created_at: str = field(default_factory=utc_now)
            updated_at: str = field(default_factory=utc_now)

            def update_status(self, status: str, result: Dict[str, Any] | None = None) -> None:
                self.status = status
                self.updated_at = utc_now()
                if result is not None:
                    self.result = result

            def to_dict(self) -> Dict[str, Any]:
                return asdict(self)

            @classmethod
            def from_dict(cls, data: Dict[str, Any]) -> "AutonomyJob":
                allowed = cls.__dataclass_fields__.keys()
                return cls(**{k: v for k, v in data.items() if k in allowed})
    ''',
    "buster/autonomy/next_actions.py": '''
        from __future__ import annotations

        from typing import Any, Dict, List


        class NextActionRecommender:
            """Rule-based next-action layer.

            This is deliberately simple and local. The AI planner can still use
            an LLM, but this layer gives Buster dependable OS-style defaults.
            """

            def recommend(self, context: Dict[str, Any]) -> Dict[str, Any]:
                request = (context.get("request") or "").lower()
                project_type = (context.get("project_type") or "general").lower()
                last_status = (context.get("last_status") or "").lower()
                error_count = int(context.get("error_count") or 0)
                has_tests = bool(context.get("has_tests", True))
                plugins = context.get("plugins") or []
                patterns = context.get("patterns") or []

                if "error" in request or "fix" in request or error_count > 0 or last_status == "failed":
                    return self._action(
                        "fix_then_verify",
                        0.92,
                        "Errors or failures detected, so Buster should repair first and verify after.",
                        ["Fixer", "Tester", "Verifier"],
                    )

                if "test" in request or not has_tests:
                    return self._action(
                        "create_or_run_tests",
                        0.86,
                        "Testing is the safest next step before deeper autonomy.",
                        ["Tester", "Verifier"],
                    )

                if any(word in request for word in ["build", "make", "create", "app", "project"]):
                    return self._action(
                        "plan_build_test_fix_verify",
                        0.88,
                        "Build request detected; use the full agent pipeline.",
                        ["Builder", "Tester", "Fixer", "Reviewer", "Verifier"],
                    )

                if any(word in request for word in ["review", "clean", "improve", "refactor"]):
                    return self._action(
                        "review_improve_verify",
                        0.82,
                        "Improvement request detected; review before changing code.",
                        ["Reviewer", "Fixer", "Verifier"],
                    )

                if project_type in ["android", "esp32", "arduino", "python"] and plugins:
                    return self._action(
                        "load_plugin_then_plan",
                        0.78,
                        "A matching plugin exists, so Buster should load capability-specific tools.",
                        ["Planner", "Builder", "Verifier"],
                    )

                if patterns:
                    return self._action(
                        "reuse_learned_pattern",
                        0.74,
                        "Relevant learned patterns exist, so reuse proven architecture first.",
                        ["Planner", "Builder", "Reviewer"],
                    )

                return self._action(
                    "inspect_then_plan",
                    0.65,
                    "No urgent signal detected; inspect context before executing.",
                    ["Planner", "Reviewer"],
                )

            def _action(self, name: str, confidence: float, reason: str, agents: List[str]) -> Dict[str, Any]:
                return {
                    "action": name,
                    "confidence": confidence,
                    "reason": reason,
                    "agents": agents,
                }
    ''',
    "buster/autonomy/engine.py": '''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any, Dict, List, Optional

        from buster.autonomy.next_actions import NextActionRecommender
        from buster.autonomy.records import AutonomyDecision, AutonomyJob, utc_now
        from buster.brain.planner.strategy_planner import StrategyPlanner
        from buster.learning import LearningEngine
        from buster.plugins.registry import PluginRegistry


        class AutonomyEngine:
            """Jarvis-level coordination layer.

            It does not replace the current Buster system. It sits above it and
            decides what Buster should do next using learning, plugins, and job state.
            """

            def __init__(
                self,
                state_path: str | Path = "data/autonomy_state.json",
                history_path: str | Path = "data/autonomy_history.json",
                learning: Optional[LearningEngine] = None,
                registry: Optional[PluginRegistry] = None,
            ) -> None:
                self.state_path = Path(state_path)
                self.history_path = Path(history_path)
                self.learning = learning or LearningEngine()
                self.registry = registry or PluginRegistry()
                self.strategy_planner = StrategyPlanner(learning=self.learning, registry=self.registry)
                self.recommender = NextActionRecommender()
                self.state_path.parent.mkdir(parents=True, exist_ok=True)
                self.history_path.parent.mkdir(parents=True, exist_ok=True)
                self._ensure_files()

            def _ensure_files(self) -> None:
                if not self.state_path.exists():
                    self.state_path.write_text(json.dumps(self.default_state(), indent=2), encoding="utf-8")
                if not self.history_path.exists():
                    self.history_path.write_text(json.dumps([], indent=2), encoding="utf-8")

            def default_state(self) -> Dict[str, Any]:
                return {
                    "enabled": False,
                    "mode": "manual",  # manual, assisted, autonomous
                    "last_decision": None,
                    "active_jobs": [],
                    "completed_jobs": 0,
                    "failed_jobs": 0,
                    "updated_at": utc_now(),
                }

            def load_state(self) -> Dict[str, Any]:
                self._ensure_files()
                return json.loads(self.state_path.read_text(encoding="utf-8"))

            def save_state(self, state: Dict[str, Any]) -> None:
                state["updated_at"] = utc_now()
                self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            def set_mode(self, mode: str) -> Dict[str, Any]:
                if mode not in {"manual", "assisted", "autonomous"}:
                    raise ValueError("mode must be manual, assisted, or autonomous")
                state = self.load_state()
                state["mode"] = mode
                state["enabled"] = mode != "manual"
                self.save_state(state)
                return state

            def decide_next_action(
                self,
                request: str,
                project_type: str = "general",
                context: Optional[Dict[str, Any]] = None,
            ) -> AutonomyDecision:
                context = dict(context or {})
                plan = self.strategy_planner.plan(request, project_type=project_type)
                plugin_names = [p.get("name", "unknown") for p in plan.get("plugins", [])]
                pattern_names = [p.get("name") or p.get("title") or str(p) for p in plan.get("reusable_patterns", [])]

                context.update({
                    "request": request,
                    "project_type": project_type,
                    "plugins": plugin_names,
                    "patterns": pattern_names,
                })
                action = self.recommender.recommend(context)
                strategy = plan.get("recommended_strategy", {}).get("name", "general")

                decision = AutonomyDecision(
                    request=request,
                    project_type=project_type,
                    recommended_action=action["action"],
                    confidence=action["confidence"],
                    reason=action["reason"],
                    strategy=strategy,
                    plugins=plugin_names,
                    patterns=pattern_names,
                )

                state = self.load_state()
                state["last_decision"] = decision.to_dict()
                self.save_state(state)
                self._append_history({"type": "decision", "decision": decision.to_dict(), "plan": plan})
                return decision

            def create_job(
                self,
                title: str,
                request: str,
                project: str = "default",
                project_type: str = "general",
                context: Optional[Dict[str, Any]] = None,
            ) -> AutonomyJob:
                decision = self.decide_next_action(request, project_type=project_type, context=context)
                agents = self.recommender.recommend({
                    "request": request,
                    "project_type": project_type,
                    "plugins": decision.plugins,
                    "patterns": decision.patterns,
                })["agents"]
                job = AutonomyJob(
                    title=title,
                    request=request,
                    project=project,
                    project_type=project_type,
                    status="queued",
                    assigned_agents=agents,
                    decision=decision.to_dict(),
                )
                state = self.load_state()
                state.setdefault("active_jobs", []).append(job.to_dict())
                self.save_state(state)
                self._append_history({"type": "job_created", "job": job.to_dict()})
                return job

            def complete_job(self, job_id: str, success: bool, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                state = self.load_state()
                active = [AutonomyJob.from_dict(j) for j in state.get("active_jobs", [])]
                kept: List[Dict[str, Any]] = []
                completed_job: Optional[AutonomyJob] = None

                for job in active:
                    if job.job_id == job_id:
                        job.update_status("completed" if success else "failed", result or {})
                        completed_job = job
                    else:
                        kept.append(job.to_dict())

                if completed_job is None:
                    raise KeyError(f"No active autonomy job with id: {job_id}")

                state["active_jobs"] = kept
                if success:
                    state["completed_jobs"] = int(state.get("completed_jobs", 0)) + 1
                else:
                    state["failed_jobs"] = int(state.get("failed_jobs", 0)) + 1
                self.save_state(state)
                self._append_history({"type": "job_completed", "success": success, "job": completed_job.to_dict()})

                # Feed the Learning Engine after every completed autonomous job.
                self.learning.learn_from_job(
                    task=completed_job.request,
                    project=completed_job.project_type,
                    success=success,
                    strategy=completed_job.decision.get("strategy", "autonomy"),
                    what_worked=(result or {}).get("what_worked", []) if success else [],
                    what_failed=(result or {}).get("what_failed", []) if not success else [],
                    fixes=(result or {}).get("fixes", []),
                    reusable_patterns=(result or {}).get("reusable_patterns", []),
                    tags=[completed_job.project_type, "autonomy"],
                )
                return completed_job.to_dict()

            def status(self) -> Dict[str, Any]:
                state = self.load_state()
                learning_summary = self.learning.summary()
                return {
                    "mode": state.get("mode", "manual"),
                    "enabled": state.get("enabled", False),
                    "active_jobs": len(state.get("active_jobs", [])),
                    "completed_jobs": state.get("completed_jobs", 0),
                    "failed_jobs": state.get("failed_jobs", 0),
                    "last_decision": state.get("last_decision"),
                    "learning": learning_summary,
                    "updated_at": state.get("updated_at"),
                }

            def _append_history(self, event: Dict[str, Any]) -> None:
                self._ensure_files()
                history = json.loads(self.history_path.read_text(encoding="utf-8"))
                event["created_at"] = utc_now()
                history.append(event)
                self.history_path.write_text(json.dumps(history[-500:], indent=2), encoding="utf-8")
    ''',
    "buster/autonomy/dashboard.py": '''
        from __future__ import annotations

        from typing import Any, Dict, Optional

        from buster.autonomy.engine import AutonomyEngine


        class AutonomyDashboard:
            """Small data provider for the AI OS dashboard.

            UI code can call snapshot() and render the returned dictionary without
            importing internals from the autonomy system.
            """

            def __init__(self, engine: Optional[AutonomyEngine] = None) -> None:
                self.engine = engine or AutonomyEngine()

            def snapshot(self) -> Dict[str, Any]:
                status = self.engine.status()
                last = status.get("last_decision") or {}
                return {
                    "title": "Jarvis Autonomy",
                    "mode": status["mode"],
                    "enabled": status["enabled"],
                    "active_jobs": status["active_jobs"],
                    "completed_jobs": status["completed_jobs"],
                    "failed_jobs": status["failed_jobs"],
                    "last_action": last.get("recommended_action", "none"),
                    "last_reason": last.get("reason", "No decision yet."),
                    "learning_records": status.get("learning", {}).get("records", 0),
                    "learned_patterns": status.get("learning", {}).get("patterns", 0),
                    "updated_at": status.get("updated_at"),
                }
    ''',
    "buster/brain/planner/autonomy_planner.py": '''
        from __future__ import annotations

        from typing import Any, Dict, Optional

        from buster.autonomy.engine import AutonomyEngine


        class AutonomyPlanner:
            """Planner bridge for Jarvis-style natural language commands."""

            def __init__(self, engine: Optional[AutonomyEngine] = None) -> None:
                self.engine = engine or AutonomyEngine()

            def plan_next(self, request: str, project_type: str = "general", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
                decision = self.engine.decide_next_action(request, project_type=project_type, context=context)
                return {
                    "request": request,
                    "project_type": project_type,
                    "next_action": decision.recommended_action,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                    "strategy": decision.strategy,
                    "plugins": decision.plugins,
                    "patterns": decision.patterns,
                }

            def queue_autonomous_job(self, title: str, request: str, project: str = "default", project_type: str = "general") -> Dict[str, Any]:
                job = self.engine.create_job(title=title, request=request, project=project, project_type=project_type)
                return job.to_dict()
    ''',
}


def main() -> None:
    print("=== Applying Buster v3.6 Jarvis Autonomy Layer Patch ===")
    for relative_path, content in FILES.items():
        write_file(relative_path, content)

    write_json_if_missing("data/autonomy_state.json", {
        "enabled": False,
        "mode": "manual",
        "last_decision": None,
        "active_jobs": [],
        "completed_jobs": 0,
        "failed_jobs": 0,
        "updated_at": None,
    })
    write_json_if_missing("data/autonomy_history.json", [])

    print("\nSUCCESS: Buster v3.6 Jarvis Autonomy Layer installed.")
    print("Next: python test_v3_6_jarvis_autonomy_layer.py")


if __name__ == "__main__":
    main()
