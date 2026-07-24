"""
Test Phase 3 Step 3: Autonomous Step-Planning Integration
"""
import pytest
from buster.runtime import create_runtime_core


def test_autonomous_step_planning(tmp_path):
    runtime = create_runtime_core(root=tmp_path)
    runtime.start()

    autonomy = runtime.service("autonomy")
    assert autonomy is not None

    # Propose a high-level goal requiring multi-step planning
    goal = "Create a project folder structure and initialize a python configuration file"
    
    # Trigger goal decomposition / planning in AutonomyEngine
    plan = autonomy.plan_goal(goal)
    
    assert plan is not None
    assert len(plan.get("steps", [])) > 0

    runtime.stop()