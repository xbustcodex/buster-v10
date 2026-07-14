from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict
from .storage import now
@dataclass
class RuntimeHeartbeat:
    tick: int = 0
    mode: str = 'companion'
    interval_seconds: float = 1.0
    created_at: str = ''
    def beat(self) -> Dict[str, Any]:
        self.tick += 1
        self.created_at = now()
        return {'tick': self.tick, 'mode': self.mode, 'timestamp': self.created_at, 'interval_seconds': self.interval_seconds}
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
