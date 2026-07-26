# tests/test_v31_git_fs.py
import pytest
from buster.capabilities import CapabilityRegistry, CapabilityExecutionContext, PermissionDeniedError
from buster.capabilities.git_cap import GitCapability
from buster.capabilities.filesystem_cap import FilesystemCapability


def test_filesystem_read_write(tmp_path):
    registry = CapabilityRegistry()
    fs_cap = FilesystemCapability(registry)
    registry.register(fs_cap)

    test_file = tmp_path / "hello.txt"
    ctx = CapabilityExecutionContext(
        mission_id="m_fs",
        task_id="t_fs",
        trace_id="tr_fs",
        agent_id="builder",
        approved_permissions=frozenset(["filesystem.read", "filesystem.write"]),
    )

    # Write file
    res_write = fs_cap.execute("filesystem.write_file", {"file_path": str(test_file), "content": "Buster v31.2 Filesystem OK"}, ctx)
    assert res_write.success is True
    assert res_write.output["bytes_written"] > 0

    # Read file
    res_read = fs_cap.execute("filesystem.read_file", {"file_path": str(test_file)}, ctx)
    assert res_read.success is True
    assert res_read.output["content"] == "Buster v31.2 Filesystem OK"


def test_filesystem_permission_denial():
    fs_cap = FilesystemCapability()
    ctx = CapabilityExecutionContext(
        mission_id="m_fs",
        task_id="t_fs",
        trace_id="tr_fs",
        agent_id="builder",
        approved_permissions=frozenset(),  # Missing permissions
    )

    with pytest.raises(PermissionDeniedError):
        fs_cap.execute("filesystem.read_file", {"file_path": "dummy.txt"}, ctx)


def test_git_capability_health_and_registration():
    registry = CapabilityRegistry()
    git_cap = GitCapability(registry)
    registry.register(git_cap)

    snapshot = registry.health_snapshot()
    assert len(snapshot) == 1
    assert snapshot[0].capability_id == "core.git"