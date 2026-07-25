"""
Test v14.4: Code and Index Step-Runner
"""
import json
import pytest
from buster.autonomy.executors.code_runner import CodeAndIndexRunner


def test_rebuild_index_runner(tmp_path):
    # Setup mock workspace
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Project", encoding="utf-8")

    runner = CodeAndIndexRunner()
    result = runner.execute_rebuild_index(workspace_root=tmp_path)

    assert result["status"] == "success"
    assert result["indexed_count"] == 2

    # Verify output file
    index_path = tmp_path / ".buster_index.json"
    assert index_path.exists()

    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data["total_files"] == 2
    assert "README.md" in data["files"]