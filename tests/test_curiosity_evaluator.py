from pathlib import Path
import pytest

from buster.learning.curiosity_evaluator import CuriosityEvaluator


def test_curiosity_evaluator_scores_files(tmp_path):
    # Create sample Python file with >150 lines
    large_file = tmp_path / "large_module.py"
    large_file.write_text("\n".join([f"# Line {i}" for i in range(200)]), encoding="utf-8")

    evaluator = CuriosityEvaluator(project_root=tmp_path)
    target = evaluator.evaluate_file(large_file)

    assert target.score > 0
    assert "High file complexity" in target.reasons[0]


def test_scan_project_ranks_targets(tmp_path):
    f1 = tmp_path / "small.py"
    f1.write_text("print('hello')", encoding="utf-8")

    f2 = tmp_path / "complex.py"
    f2.write_text("\n".join([f"x = {i}" for i in range(250)]), encoding="utf-8")

    evaluator = CuriosityEvaluator(project_root=tmp_path)
    results = evaluator.scan_project(limit=5)

    assert len(results) >= 1
    assert results[0].target_path.endswith("complex.py")