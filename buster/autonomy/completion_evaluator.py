# buster/autonomy/completion_evaluator.py
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from buster.autonomy.mission_state import Mission

logger = logging.getLogger(__name__)


@dataclass
class VerificationEvidence:
    acceptance_criteria_satisfied: bool
    tests_passed: bool
    verification_report_passed: bool
    active_leases_count: int
    unresolved_critical_failures: bool
    pending_approval: bool


@dataclass
class CompletionDecision:
    status: str  # COMPLETE, INCOMPLETE, NEEDS_VERIFICATION, NEEDS_APPROVAL, BLOCKED
    reason: str
    missing_evidence: List[str] = field(default_factory=list)


class CompletionEvaluator:
    """Rigorously evaluates evidence before allowing Buster to mark a mission as complete."""

    def evaluate(self, mission: Mission, evidence: VerificationEvidence) -> CompletionDecision:
        missing = []

        if not evidence.acceptance_criteria_satisfied:
            missing.append("acceptance_criteria_satisfied")
        if not evidence.tests_passed:
            missing.append("tests_passed")
        if not evidence.verification_report_passed:
            missing.append("verification_report_passed")
        if evidence.active_leases_count > 0:
            missing.append("active_leases_released")
        if evidence.unresolved_critical_failures:
            missing.append("unresolved_critical_failures_resolved")
        if evidence.pending_approval:
            missing.append("pending_approval_cleared")

        if missing:
            logger.warning(f"Mission [{mission.mission_id}] completion evaluation failed. Missing evidence: {missing}")
            return CompletionDecision(
                status="NEEDS_VERIFICATION" if not evidence.pending_approval else "NEEDS_APPROVAL",
                reason=f"Mission cannot complete due to unverified evidence items.",
                missing_evidence=missing,
            )

        logger.info(f"Mission [{mission.mission_id}] passed all evidence checks. Marked COMPLETE.")
        return CompletionDecision(
            status="COMPLETE",
            reason="All acceptance criteria, test suites, and lease requirements successfully verified.",
        )