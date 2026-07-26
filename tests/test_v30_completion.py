# tests/test_v30_completion.py
import pytest
from buster.autonomy.mission_state import Mission
from buster.autonomy.completion_evaluator import CompletionEvaluator, VerificationEvidence


def test_completion_requires_verification_evidence():
    evaluator = CompletionEvaluator()
    mission = Mission(
        mission_id="m_comp_1",
        objective="Feature deployment",
        status="VERIFYING",
        priority=1,
        created_at="2026-07-26T04:06:00Z",
        current_stage="VERIFYING",
    )

    # Incomplete evidence (tests failed)
    bad_evidence = VerificationEvidence(
        acceptance_criteria_satisfied=True,
        tests_passed=False,
        verification_report_passed=True,
        active_leases_count=0,
        unresolved_critical_failures=False,
        pending_approval=False,
    )

    decision = evaluator.evaluate(mission, bad_evidence)
    assert decision.status == "NEEDS_VERIFICATION"
    assert "tests_passed" in decision.missing_evidence

    # Perfect evidence
    good_evidence = VerificationEvidence(
        acceptance_criteria_satisfied=True,
        tests_passed=True,
        verification_report_passed=True,
        active_leases_count=0,
        unresolved_critical_failures=False,
        pending_approval=False,
    )

    complete_decision = evaluator.evaluate(mission, good_evidence)
    assert complete_decision.status == "COMPLETE"