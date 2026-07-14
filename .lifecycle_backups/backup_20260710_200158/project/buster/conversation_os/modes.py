from __future__ import annotations


class TalkMode:
    SILENT = "silent"
    QUIET = "quiet"
    BALANCED = "balanced"
    TALKATIVE = "talkative"
    JARVIS = "jarvis"


class SpeechPriority:
    LOW = "low"
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"


PRIORITY_SCORE = {
    SpeechPriority.LOW: 1,
    SpeechPriority.NORMAL: 2,
    SpeechPriority.IMPORTANT: 3,
    SpeechPriority.URGENT: 4,
}
