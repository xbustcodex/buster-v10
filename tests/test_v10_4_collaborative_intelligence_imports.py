def test_v10_4_collaborative_intelligence_imports():
    from buster.runtime import (
        RuntimeBlackboard,
        AgentMemory,
        AgentOrchestrator,
        OrchestratorAgent,
    )

    assert RuntimeBlackboard is not None
    assert AgentMemory is not None
    assert AgentOrchestrator is not None
    assert OrchestratorAgent is not None
