from dataclasses import dataclass

@dataclass
class Intent:
    name: str
    target: str = ""
    confidence: float = 0.0
    raw: str = ""

@dataclass
class Plan:
    intent: Intent
    action: str
    target: str = ""
    agent: str = ""
    status: str = "planned"
