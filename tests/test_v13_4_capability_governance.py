"""
Test v13.3: Capability-Based Governance Matrix
"""
import pytest
from buster.autonomy.goals.approval_policy import ApprovalPolicy
from buster.autonomy.goals.capabilities import Capability, CapabilityPolicy, ExecutionPermission
from buster.autonomy.goals.models import GoalProposal


def test_capability_governance_rules():
    policy = ApprovalPolicy()

    # 1. INDEX / READ goals map to READ_FILES and auto-approve
    read_proposal = GoalProposal(
        title="Rebuild index",
        request="Scan project and inspect files",
        target="/workspace/index.json",
        signal_id="sig_001",
    )
    eval_read = policy.evaluate(read_proposal)
    assert eval_read.is_approved is True

    # 2. Explicit WRITE goals map to WRITE_FILES and prompt user
    write_proposal = GoalProposal(
        title="Write build logs",
        request="Write update to disk",
        target="/workspace/build.log",
        signal_id="sig_002",
    )
    eval_write = policy.evaluate(write_proposal)
    assert eval_write.is_approved is False

    # 3. GIT COMMIT auto-approves under default matrix
    commit_proposal = GoalProposal(
        title="Git commit auto-save",
        request="Perform local git commit",
        target="/workspace/repo",
        signal_id="sig_003",
    )
    eval_commit = policy.evaluate(commit_proposal)
    assert eval_commit.is_approved is True

    # 4. Custom matrix overrides: enable WRITE_FILES auto-approval
    custom_policy = CapabilityPolicy({Capability.WRITE_FILES: ExecutionPermission.AUTO_APPROVE})
    custom_approval = ApprovalPolicy(capability_policy=custom_policy)
    eval_write_custom = custom_approval.evaluate(write_proposal)
    assert eval_write_custom.is_approved is True