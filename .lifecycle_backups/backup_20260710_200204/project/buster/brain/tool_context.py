from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolContext:
    user_input: str
    route: str = "local"
    local_context: str = ""
    web_context: str = ""
    project_context: str = ""
    agent_notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def merged_context(self) -> str:
        parts = []
        if self.local_context:
            parts.append("[LOCAL]\n" + self.local_context)
        if self.web_context:
            parts.append("[WEB]\n" + self.web_context)
        if self.project_context:
            parts.append("[PROJECT]\n" + self.project_context)
        if self.agent_notes:
            parts.append("[AGENT NOTES]\n" + "\n".join(self.agent_notes))
        return "\n\n".join(parts)
