from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Any, List

class VisualPatternEngine:
    def discover_patterns(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        labels = [o.get("label", "unknown") for o in observations]; contexts = [o.get("context", "") for o in observations if o.get("context")]; out = []
        for label, count in Counter(labels).items():
            if count >= 2: out.append({"type": "repeated_visual_label", "label": label, "count": count, "confidence": min(0.99, 0.50 + count * 0.10), "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "recommendation": f"Remember visual pattern: {label}"})
        for context, count in Counter(contexts).items():
            if count >= 2: out.append({"type": "repeated_visual_context", "context": context, "count": count, "confidence": min(0.99, 0.50 + count * 0.10), "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "recommendation": f"This visual context appears often: {context}"})
        return out
