# tests/test_v32_context.py
import pytest
from buster.orchestration.context import MissionContext


def test_mission_context_resolution():
    ctx = MissionContext(mission_id="mission_test_123", initial_variables={"env": "production"})
    ctx.set_output("t1", {"file_path": "/tmp/output.txt", "status": "success"})

    # Test direct lookup and interpolation
    assert ctx.resolve_value("{outputs.t1.file_path}") == "/tmp/output.txt"
    assert ctx.resolve_value("{variables.env}") == "production"
    assert ctx.resolve_value("File saved at {outputs.t1.file_path} for {variables.env}") == "File saved at /tmp/output.txt for production"

    # Test nested dict resolution
    nested_args = {
        "path": "{outputs.t1.file_path}",
        "mode": "read",
        "nested": {"env": "{variables.env}"}
    }
    resolved = ctx.resolve_value(nested_args)
    assert resolved["path"] == "/tmp/output.txt"
    assert resolved["nested"]["env"] == "production"