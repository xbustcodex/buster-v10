from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .confidence import ConfidenceEngine
from .decision_tree import DecisionTree
from .risk_analysis import RiskAnalyzer
from .strategy_selector import StrategySelector


@dataclass
class ReasoningResult:
    request: str
    strategy: Dict[str, Any]
    risk: Dict[str, Any]
    confidence: Dict[str, Any]
    decision: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request,
            "strategy": self.strategy,
            "risk": self.risk,
            "confidence": self.confidence,
            "decision": self.decision,
        }


class ReasoningEngine:
    def __init__(self) -> None:
        self.strategy_selector = StrategySelector()
        self.risk_analyzer = RiskAnalyzer()
        self.confidence_engine = ConfidenceEngine()
        self.decision_tree = DecisionTree()

    def reason(self, request: str, context: Dict[str, Any] | None = None) -> ReasoningResult:
        context = context or {}
        strategy = self.strategy_selector.select(request, context)
        risk = self.risk_analyzer.analyze(request, context)

        signals = dict(context)
        signals["known_strategy"] = bool(strategy.name)
        signals["high_risk"] = risk.level in {"high", "blocked"}
        signals["destructive_action"] = "destructive_action" in risk.risks

        confidence = self.confidence_engine.score(signals)
        decision = self.decision_tree.decide(confidence.to_dict(), risk.to_dict())

        return ReasoningResult(request, strategy.to_dict(), risk.to_dict(), confidence.to_dict(), decision)
