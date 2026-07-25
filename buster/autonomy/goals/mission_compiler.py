from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from buster.autonomy.goals.models import GoalProposal


@dataclass
class MissionSpec:
    mission_id: str
    goal_id: str
    title: str
    target: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class MissionCompiler:
    """Translates high-level goal proposals into actionable execution mission specifications."""

    def compile(self, proposal: GoalProposal, evidence: Optional[Dict[str, Any]] = None) -> MissionSpec:
        evidence = evidence or {}
        title_lower = proposal.title.lower()

        # Generate structured execution steps based on goal intent
        if "index" in title_lower:
            steps = [
                {"action": "scan_directory", "path": proposal.target},
                {"action": "extract_metadata", "target": proposal.target},
                {"action": "write_index_file", "target": proposal.target},
            ]
        elif "commit" in title_lower:
            steps = [
                {"action": "git_status", "repo": proposal.target},
                {"action": "git_add", "files": ["."]},
                {"action": "git_commit", "message": f"Auto-commit: {proposal.title}"},
            ]
        else:
            steps = [
                {"action": "inspect_target", "target": proposal.target},
                {"action": "execute_generic_task", "request": proposal.request},
            ]

        return MissionSpec(
            mission_id=f"mission_{proposal.id}",
            goal_id=proposal.id,
            title=proposal.title,
            target=proposal.target,
            steps=steps,
            context={"evidence": evidence, "signal_id": proposal.signal_id},
        )