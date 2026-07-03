from __future__ import annotations

from typing import Iterable


def weighted_average(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 2)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
