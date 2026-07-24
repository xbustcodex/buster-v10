"""
Test Phase 3: Autonomy & Guardrails Integration
"""
import pytest
from pathlib import Path
from buster.runtime import create_runtime_core


def test_sandbox_guardrail_execution(tmp_path):
    runtime = create_runtime_core(root=tmp_path)
    runtime.start()

    # Verify Sandbox Manager is active in runtime
    sandbox_mgr = runtime.service("sandbox_manager")
    assert sandbox_mgr is not None

    # Create an isolated environment for execution
    sandbox_id = sandbox_mgr.create_sandbox("autonomy_test")
    assert sandbox_id in sandbox_mgr.active_sandboxes

    # Verify router is available
    router = runtime.service("automation_router")
    assert router is not None
    assert router.status()["status"] == "active"

    # Clean up
    sandbox_mgr.cleanup_all()
    runtime.stop()