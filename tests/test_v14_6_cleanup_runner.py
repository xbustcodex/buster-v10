"""
Test v14.6: Workspace Cleanup Step-Runner
"""
import time
import pytest
from buster.autonomy.executors.cleanup_runner import WorkspaceCleanupRunner


def test_purge_artifacts(tmp_path):
    # Setup mock workspace files
    temp_file = tmp_path / "scratch.tmp"
    temp_file.write_text("temporary data", encoding="utf-8")

    keep_file = tmp_path / "main.py"
    keep_file.write_text("print('keep me')", encoding="utf-8")

    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "main.pyc").write_text("compiled", encoding="utf-8")

    runner = WorkspaceCleanupRunner()
    result = runner.purge_artifacts(
        workspace_root=tmp_path,
        patterns=["*.tmp", "__pycache__"],
    )

    assert result["status"] == "success"
    assert result["purged_count"] == 2
    assert not temp_file.exists()
    assert not cache_dir.exists()
    assert keep_file.exists()