from __future__ import annotations

class PresenceMode:
    SILENT = "silent"
    ASSISTANT = "assistant"
    COMPANION = "companion"
    ENGINEER = "engineer"

class EmotionalState:
    RELAXED = "relaxed"
    THINKING = "thinking"
    WORKING = "working"
    INVESTIGATING = "investigating"
    LEARNING = "learning"
    CONCERNED = "concerned"
    SATISFIED = "satisfied"

class PresencePriority:
    LOW = "low"
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"

PRIORITY_SCORE = {PresencePriority.LOW: 1, PresencePriority.NORMAL: 2, PresencePriority.IMPORTANT: 3, PresencePriority.URGENT: 4}

def state_for_activity(activity: str) -> str:
    text = (activity or "").lower()
    if any(word in text for word in ["error", "failed", "failure", "crash"]): return EmotionalState.CONCERNED
    if any(word in text for word in ["fix", "investigate", "debug"]): return EmotionalState.INVESTIGATING
    if any(word in text for word in ["build", "run", "generate", "working"]): return EmotionalState.WORKING
    if any(word in text for word in ["plan", "think", "strategy", "decide"]): return EmotionalState.THINKING
    if any(word in text for word in ["learn", "pattern", "experience"]): return EmotionalState.LEARNING
    if any(word in text for word in ["complete", "success", "approved", "passed"]): return EmotionalState.SATISFIED
    return EmotionalState.RELAXED
