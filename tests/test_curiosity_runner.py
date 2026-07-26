from pathlib import Path
import pytest

from buster.learning.curiosity_scheduler import ExplorationTask
from buster.learning.curiosity_runner import CuriosityRunner


def test_curiosity_runner_inspects_valid_python_file(tmp_path):
    target_file = tmp_path / "sample.py"
    target_file.write_text(
        "class Demo:\n"
        "    def hello(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    task = ExplorationTask(
        task_id="test_001",
        target_path="sample.py",
        curiosity_score=15.0,
        reasons=["High complexity"],
    )

    runner = CuriosityRunner(project_root=tmp_path)
    result = runner.inspect_target(task)

    assert result.success is True
    assert result.metadata["class_count"] == 1
    assert result.metadata["function_count"] == 1


def test_curiosity_runner_handles_syntax_error(tmp_path):
    target_file = tmp_path / "broken.py"
    target_file.write_text("def broken_syntax(:", encoding="utf-8")

    task = ExplorationTask(
        task_id="test_002",
        target_path="broken.py",
        curiosity_score=20.0,
        reasons=["Failure history"],
    )

    runner = CuriosityRunner(project_root=tmp_path)
    result = runner.inspect_target(task)

    assert result.success is False
    assert "SyntaxError" in result.issues_found[0]