from typing import Any, Dict, List

class ContextPrioritizer:
    def score(self, item: Dict[str, Any]) -> float:
        priority = float(item.get("priority", 5))
        confidence = float(item.get("confidence", 0.75))
        risk = str(item.get("risk", "medium")).lower()
        risk_bonus = {"low": 0.0, "medium": 1.0, "high": 2.0, "critical": 3.0}.get(risk, 1.0)
        age_penalty = float(item.get("age_penalty", 0))
        return max(0.0, priority + risk_bonus + confidence - age_penalty)

    def sort(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(items, key=self.score, reverse=True)

    def top(self, items: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        return self.sort(items)[:limit]
