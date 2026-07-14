from buster.workspace.runtime import WorkspaceSnapshot

def test_snapshot():

    snap = WorkspaceSnapshot().snapshot()

    assert "Project:" in snap
    assert "Git" in snap
    assert "Python" in snap
