def test_v10_3_multi_agent_imports():
    from buster.runtime import (
        PlannerAgent,
        BuilderAgent,
        TesterAgent,
        ReviewerAgent,
        FixerAgent,
        MultiAgentWorkflowRunner,
    )

    assert PlannerAgent is not None
    assert BuilderAgent is not None
    assert TesterAgent is not None
    assert ReviewerAgent is not None
    assert FixerAgent is not None
    assert MultiAgentWorkflowRunner is not None
