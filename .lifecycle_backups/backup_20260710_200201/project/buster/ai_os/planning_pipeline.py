from typing import Any, Dict, List


class PlanningPipeline:
    """Small integration layer that turns a user request into one unified AI OS plan."""

    def classify(self, request: str) -> str:
        text = (request or "").lower()
        if any(w in text for w in ("build", "create", "make", "app", "project")):
            return "build"
        if any(w in text for w in ("fix", "error", "bug", "failed", "crash")):
            return "fix"
        if any(w in text for w in ("test", "verify", "check")):
            return "verify"
        if any(w in text for w in ("index", "repo", "repository", "scan")):
            return "repository"
        return "general"

    def strategy_for(self, intent: str) -> List[str]:
        strategies = {
            "build": ["repository", "learning", "experience", "builder", "tester", "reviewer", "verifier", "learning"],
            "fix": ["repository", "experience", "fixer", "tester", "verifier", "learning"],
            "verify": ["tester", "reviewer", "verifier", "experience"],
            "repository": ["repository", "knowledge", "mission_control"],
            "general": ["brain", "planner", "mission_control"],
        }
        return strategies.get(intent, strategies["general"])

    def agents_for(self, intent: str) -> List[str]:
        agents = {
            "build": ["Builder", "Tester", "Reviewer", "Verifier"],
            "fix": ["Fixer", "Tester", "Verifier"],
            "verify": ["Tester", "Reviewer", "Verifier"],
            "repository": ["Repository"],
            "general": ["Planner"],
        }
        return agents.get(intent, agents["general"])

    def make_plan(self, request: str) -> Dict[str, Any]:
        intent = self.classify(request)
        strategy = self.strategy_for(intent)
        agents = self.agents_for(intent)
        return {
            "request": request,
            "intent": intent,
            "strategy": strategy,
            "agents": agents,
            "requires_confirmation": intent in ("fix",) and len(request.strip()) < 12,
        }
