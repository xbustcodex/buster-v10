from __future__ import annotations

import enum
from typing import Dict, List, Set, Optional


class WorkerRole(str, enum.Enum):
    BUILDER = "BUILDER"
    TESTER = "TESTER"
    FIXER = "FIXER"
    REVIEWER = "REVIEWER"
    RESEARCH = "RESEARCH"


class AgentCapabilityMatrix:
    """Maps required task capabilities to specialized worker agent roles."""

    CAPABILITY_MAP: Dict[WorkerRole, Set[str]] = {
        WorkerRole.BUILDER: {"code_generation", "refactoring", "scaffolding", "workspace_write"},
        WorkerRole.TESTER: {"unit_testing", "integration_testing", "coverage_report", "test_execution"},
        WorkerRole.FIXER: {"bug_fixing", "diagnostics_repair", "patching", "retry_recovery"},
        WorkerRole.REVIEWER: {"code_review", "security_audit", "style_check", "static_analysis"},
        WorkerRole.RESEARCH: {"workspace_search", "indexing", "context_retrieval", "git_status"},
    }

    @classmethod
    def resolve_role_for_task(cls, required_capabilities: List[str]) -> Optional[WorkerRole]:
        """Finds the best matching WorkerRole that satisfies all required capabilities."""
        required_set = set(required_capabilities)

        best_role: Optional[WorkerRole] = None
        best_overlap = -1

        for role, caps in cls.CAPABILITY_MAP.items():
            overlap = len(required_set.intersection(caps))
            if overlap > best_overlap and required_set.issubset(caps):
                best_role = role
                best_overlap = overlap

        # Fallback to BUILDER if no specific match found but capabilities requested
        return best_role or (WorkerRole.BUILDER if required_capabilities else None)

    @classmethod
    def get_capabilities_for_role(cls, role: WorkerRole) -> List[str]:
        """Returns the capability list for a given WorkerRole."""
        return sorted(list(cls.CAPABILITY_MAP.get(role, set())))