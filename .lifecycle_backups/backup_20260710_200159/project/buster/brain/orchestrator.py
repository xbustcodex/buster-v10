from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from buster.brain.providers.mode_detector import AIModeDetector
from buster.brain.providers.provider_modes import ProviderModeController
from buster.brain.tool_executor import ToolExecutor
from buster.brain.tool_router import ToolDecision, ToolRouter


@dataclass
class OrchestrationPlan:
    user_input: str
    route: str
    ai_mode: str
    reason: str
    confidence: float
    should_use_web: bool = False
    should_use_project: bool = False
    should_use_agents: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    plan: OrchestrationPlan
    context: str
    reply: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedIntelligenceOrchestrator:
    """
    Buster v7.6 unified intelligence layer.

    Purpose:
    - Decide the route.
    - Decide AI mode.
    - Execute the relevant tool context.
    - Return one clean orchestration result.

    This makes voice, GUI, typed chat, web, project, and agent work flow
    through the same decision layer.
    """

    def __init__(
        self,
        router: ToolRouter | None = None,
        executor: ToolExecutor | None = None,
        mode_detector: AIModeDetector | None = None,
        mode_controller: ProviderModeController | None = None,
    ):
        self.router = router or ToolRouter()
        self.executor = executor or ToolExecutor()
        self.mode_detector = mode_detector or AIModeDetector()
        self.mode_controller = mode_controller or ProviderModeController()

    def make_plan(self, user_input: str, *, voice: bool = False, context: Optional[Dict[str, Any]] = None) -> OrchestrationPlan:
        decision: ToolDecision = self.router.decide(user_input, context=context or {})
        ai_mode = self.mode_detector.detect(user_input, voice=voice)

        # Keep routing and mode coherent.
        if decision.tool == "web":
            casual_voice = voice and any(
                phrase in user_input.lower()
                for phrase in ["how are you today", "how are you", "you ok", "what's up"]
            )
            if casual_voice:
                ai_mode = "voice"
            else:
                ai_mode = "research"
        elif decision.tool == "agent":
            ai_mode = "coding"
        elif voice and ai_mode == "default":
            ai_mode = "voice"

        return OrchestrationPlan(
            user_input=user_input,
            route=decision.tool,
            ai_mode=ai_mode,
            reason=decision.reason,
            confidence=decision.confidence,
            should_use_web=decision.tool == "web",
            should_use_project=decision.tool == "project",
            should_use_agents=decision.tool == "agent",
            metadata={
                "decision": decision.metadata,
                "voice": voice,
            },
        )

    def gather_context(self, plan: OrchestrationPlan):
        decision = ToolDecision(
            tool=plan.route,
            reason=plan.reason,
            confidence=plan.confidence,
            metadata=plan.metadata.get("decision", {}),
        )
        return self.executor.execute(decision, plan.user_input)

    def orchestrate(self, user_input: str, *, voice: bool = False, context: Optional[Dict[str, Any]] = None) -> OrchestrationResult:
        plan = self.make_plan(user_input, voice=voice, context=context)
        self.mode_controller.set_mode(plan.ai_mode)
        tool_context = self.gather_context(plan)

        return OrchestrationResult(
            plan=plan,
            context=tool_context.merged_context(),
            metadata={
                "tool_context": tool_context.metadata,
                "mode_status": self.mode_controller.status(),
            },
        )

    def explain_plan(self, plan: OrchestrationPlan) -> str:
        return (
            f"Route: {plan.route}\n"
            f"AI mode: {plan.ai_mode}\n"
            f"Reason: {plan.reason}\n"
            f"Confidence: {int(plan.confidence * 100)}%"
        )
