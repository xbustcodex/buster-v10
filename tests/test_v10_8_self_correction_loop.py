"""
Test Phase 3 Step 2: Self-Correction Loop Integration
"""
import pytest
from pathlib import Path
from buster.runtime import create_runtime_core


def test_self_correction_loop_execution(tmp_path):
    runtime = create_runtime_core(root=tmp_path)
    runtime.start()

    # Create dummy target python file needing repair/correction
    test_file = tmp_path / "failing_script.py"
    test_file.write_text("def add(a, b):\n    return a - b  # Bug: minus instead of plus\n")

    # Run repair through runtime core
    # The agent worker should run, validate, and fix the script
    diff = runtime.run_python_repair(
        file_path=test_file,
        instruction="Fix the add function to perform addition, not subtraction.",
    )

    assert diff is not None
    assert diff.success is True

    runtime.stop()