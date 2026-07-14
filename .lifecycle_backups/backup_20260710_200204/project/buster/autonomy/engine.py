from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

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
