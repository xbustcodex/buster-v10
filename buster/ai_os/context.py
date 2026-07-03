from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AIOSContext:
    root: Path = field(default_factory=lambda: Path.cwd())
    user_request: str = ""
    project_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def data_path(self, name: str) -> Path:
        p = self.root / "data" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
