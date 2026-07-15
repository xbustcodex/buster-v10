from dataclasses import dataclass
from typing import Any

@dataclass
class RuntimeEvent:
    timestamp: str
    event_type: str
    source: str
    payload: dict[str, Any]