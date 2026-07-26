import sys
from pathlib import Path
import pytest

from buster.hurdle.classifier import Hurdle
from buster.hurdle.patch_generator import PatchGenerator
from buster.hurdle.patch_verifier import PatchVerifier


def test_patch_verifier_applies_valid_patch(tmp_path):
    module_file = tmp_path / "solution.py"
    module_file.write_text("def solve():\n    return False\n", encoding="utf-8")

    test_file = tmp_path / "test_solution.py"
    test_file.write_text(
        "from solution import solve\n"
        "def test_solve():\n"
        "    assert solve() is True\n",
        encoding="utf-8",
    )

    hurdle = Hurdle(
        hurdle_id="h1",
        error_type="AssertionError",
        message="Failed",
        file_path="solution.py",
        line_number=2,
        stack_trace="",
    )

    generator = PatchGenerator(project_root=tmp_path)
    candidate = generator.generate_candidate_patch(
        hurdle=hurdle,
        replacement_code="def solve():\n    return True\n",
    )

    verifier = PatchVerifier(project_root=tmp_path)
    result = verifier.verify_and_apply(
        candidate=candidate,
        test_command=[sys.executable, "-m", "pytest", "test_solution.py"],
    )

    assert result.tests_passed is True
    assert result.applied is True
    assert result.rollback_performed is False
    assert module_file.read_text(encoding="utf-8") == "def solve():\n    return True\n"


def test_patch_verifier_auto_rolls_back_on_test_failure(tmp_path):
    module_file = tmp_path / "solution.py"
    original_code = "def solve():\n    return False\n"
    module_file.write_text(original_code, encoding="utf-8")

    test_file = tmp_path / "test_solution.py"
    test_file.write_text(
        "from solution import solve\n"
        "def test_solve():\n"
        "    assert solve() is True\n",
        encoding="utf-8",
    )

    hurdle = Hurdle(
        hurdle_id="h2",
        error_type="AssertionError",
        message="Failed",
        file_path="solution.py",
        line_number=2,
        stack_trace="",
    )

    generator = PatchGenerator(project_root=tmp_path)
    # Patch still leaves assertion failing
    candidate = generator.generate_candidate_patch(
        hurdle=hurdle,
        replacement_code="def solve():\n    return False # wrong\n",
    )

    verifier = PatchVerifier(project_root=tmp_path)
    result = verifier.verify_and_apply(
        candidate=candidate,
        test_command=[sys.executable, "-m", "pytest", "test_solution.py"],
    )

    assert result.tests_passed is False
    assert result.applied is False
    assert result.rollback_performed is True
    # Verify file was rolled back to original content
    assert module_file.read_text(encoding="utf-8") == original_code