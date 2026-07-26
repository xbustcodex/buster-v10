from pathlib import Path
import pytest

from buster.hurdle.classifier import Hurdle
from buster.hurdle.patch_generator import PatchGenerator


def test_patch_generator_validates_syntax(tmp_path):
    target_file = tmp_path / "target_module.py"
    target_file.write_text("def solve():\n    return False\n", encoding="utf-8")

    hurdle = Hurdle(
        hurdle_id="h123",
        error_type="AssertionError",
        message="Expected True got False",
        file_path="target_module.py",
        line_number=2,
        stack_trace="",
    )

    generator = PatchGenerator(project_root=tmp_path)

    # Valid replacement code
    valid_candidate = generator.generate_candidate_patch(
        hurdle=hurdle,
        replacement_code="def solve():\n    return True\n",
        description="Fix return value",
    )
    assert valid_candidate.is_valid_syntax is True

    # Invalid replacement code (syntax error)
    invalid_candidate = generator.generate_candidate_patch(
        hurdle=hurdle,
        replacement_code="def solve():\n    return (",
        description="Broken patch",
    )
    assert invalid_candidate.is_valid_syntax is False