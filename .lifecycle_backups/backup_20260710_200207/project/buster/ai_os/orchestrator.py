from datetime import datetime, timezone
from typing import Any, Dict

from .context import AIOSContext
from .integration import AIOSIntegration
from .planning_pipeline import PlanningPipeline
from .status import AIOSStatus
from .storage import read_json, write_json


class AIOSOrchestrator:
    """Unified Buster AI OS brain glue.

    This does not replace existing modules. It coordinates them into one OS status.
    """

    def __init__(self, context: AIOSContext | None = None):
        self.context = context or AIOSContext()
        self.pipeline = PlanningPipeline()
        self.integration = AIOSIntegration(self.context)

    def plan(self, request: str) -> Dict[str, Any]:
        base_plan = self.pipeline.make_plan(request)
        integrated = self.integration.summarize()
        confidence = self._confidence(base_plan, integrated)
        risk = self._risk(base_plan, confidence)
        plan = {
            **base_plan,
            "confidence": confidence,
            "risk": risk,
            "integrated": integrated,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._record_event("PLAN_CREATED", plan)
        self._write_status(plan)
        return plan

    def status(self) -> AIOSStatus:
        data = read_json(self.context.data_path("ai_os_status.json"), {})
        if not data:
            integrated = self.integration.summarize()
            return AIOSStatus(
                confidence=0.0,
                plugins_loaded=integrated["plugins_loaded"],
                learning_items=integrated["learning_items"],
                experience_items=integrated["experience_items"],
                events_recorded=integrated["events_recorded"],
            )
        return AIOSStatus(**data)

    def _confidence(self, plan: Dict[str, Any], integrated: Dict[str, Any]) -> float:
        score = 0.55
        if integrated.get("learning_items", 0) > 0:
            score += 0.10
        if integrated.get("experience_items", 0) > 0:
            score += 0.12
        if integrated.get("plugins_loaded", 0) > 0:
            score += 0.08
        if plan.get("intent") in ("build", "fix", "verify"):
            score += 0.08
        if plan.get("requires_confirmation"):
            score -= 0.20
        return round(max(0.0, min(score, 0.99)), 2)

    def _risk(self, plan: Dict[str, Any], confidence: float) -> str:
        if plan.get("requires_confirmation"):
            return "needs_confirmation"
        if confidence >= 0.85:
            return "low"
        if confidence >= 0.65:
            return "medium"
        return "high"

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        path = self.context.data_path("event_history.json")
        history = read_json(path, {"events": []})
        if isinstance(history, list):
            history = {"events": history}
        history.setdefault("events", [])
        history["events"].append({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "payload": {
                "intent": payload.get("intent"),
                "confidence": payload.get("confidence"),
                "risk": payload.get("risk"),
                "strategy": payload.get("strategy", []),
            },
        })
        history["events"] = history["events"][-250:]
        write_json(path, history)

    def _write_status(self, plan: Dict[str, Any]) -> None:
        integrated = plan.get("integrated", {})
        status = AIOSStatus(
            online=True,
            mode="planning",
            current_mission=plan.get("request") or "Waiting for command",
            confidence=plan.get("confidence", 0.0),
            risk=plan.get("risk", "unknown"),
            strategy=plan.get("strategy", []),
            active_agents=plan.get("agents", []),
            plugins_loaded=integrated.get("plugins_loaded", 0),
            learning_items=integrated.get("learning_items", 0),
            experience_items=integrated.get("experience_items", 0),
            events_recorded=integrated.get("events_recorded", 0),
        )
        write_json(self.context.data_path("ai_os_status.json"), status.as_dict())
        write_json(self.context.data_path("mission_control_unified.json"), {
            "title": "Buster AI OS Mission Control",
            "status": status.as_dict(),
            "plan": plan,
        })
