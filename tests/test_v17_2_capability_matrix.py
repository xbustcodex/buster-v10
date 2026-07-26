"""
Test v17.2: Agent Capability Matrix & Task Routing
"""
import pytest
from buster.autonomy.delegation.capability_matrix import AgentCapabilityMatrix, WorkerRole


def test_resolve_role_tester():
    role = AgentCapabilityMatrix.resolve_role_for_task(["unit_testing", "test_execution"])
    assert role == WorkerRole.TESTER


def test_resolve_role_fixer():
    role = AgentCapabilityMatrix.resolve_role_for_task(["bug_fixing", "patching"])
    assert role == WorkerRole.FIXER


def test_resolve_role_research():
    role = AgentCapabilityMatrix.resolve_role_for_task(["workspace_search", "indexing"])
    assert role == WorkerRole.RESEARCH


def test_fallback_to_builder():
    role = AgentCapabilityMatrix.resolve_role_for_task(["unknown_custom_cap"])
    assert role == WorkerRole.BUILDER