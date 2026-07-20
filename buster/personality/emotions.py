# buster/personality/emotions.py
from typing import Dict

class BusterEmotionalState:
    """Maintains transient internal state indicators that influence LLM tone variables."""
    
    def __init__(self):
        self.confidence: float = 80.0
        self.focus: float = 85.0
        self.concern: float = 15.0
        self.pride: float = 75.0
        self.energy: float = 70.0

    def process_outcome(self, success: bool, impact_weight: float = 1.0):
        """Alters short-term states based on execution confirmations."""
        if success:
            self.confidence = min(100.0, self.confidence + (5.0 * impact_weight))
            self.pride = min(100.0, self.pride + (8.0 * impact_weight))
            self.concern = max(0.0, self.concern - (10.0 * impact_weight))
            self.energy = min(100.0, self.energy + (3.0 * impact_weight))
        else:
            self.confidence = max(20.0, self.confidence - (10.0 * impact_weight))
            self.pride = max(30.0, self.pride - (5.0 * impact_weight))
            self.concern = min(100.0, self.concern + (15.0 * impact_weight))
            self.focus = min(100.0, self.focus + 5.0)  # Focus sharpens during failures

    def decay_and_stabilize(self):
        """Gradually returns states toward safe baselines over idle time."""
        self.confidence = self._approach_baseline(self.confidence, 75.0, 1.0)
        self.focus = self._approach_baseline(self.focus, 80.0, 1.0)
        self.concern = self._approach_baseline(self.concern, 20.0, 1.5)
        self.pride = self._approach_baseline(self.pride, 70.0, 1.0)
        self.energy = self._approach_baseline(self.energy, 65.0, 0.5)

    def _approach_baseline(self, current: float, baseline: float, step: float) -> float:
        if current > baseline:
            return max(baseline, current - step)
        return min(baseline, current + step)

    def to_dict(self) -> Dict[str, int]:
        return {
            "Confidence": int(self.confidence),
            "Focus": int(self.focus),
            "Concern": int(self.concern),
            "Pride": int(self.pride),
            "Energy": int(self.energy)
        }