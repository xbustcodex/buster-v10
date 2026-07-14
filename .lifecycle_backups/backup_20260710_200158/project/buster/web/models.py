from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

@dataclass
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "unknown"
    score: float = 0.0

@dataclass
class WebPage:
    url: str
    title: str = ""
    text: str = ""
    status_code: int = 0
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebResult:
    query: str
    answer: str
    used_web: bool
    sources: List[WebSearchResult] = field(default_factory=list)
    pages: List[WebPage] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
