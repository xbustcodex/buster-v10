from pathlib import Path
import pytest

from buster.hurdle.classifier import HurdleClassifier


def test_classify_exception_captures_details(tmp_path):
    target_file = tmp_path / "buggy.py"
    target_file.write_text("def div():\n    return 1 / 0\n", encoding="utf-8")

    classifier = HurdleClassifier(project_root=tmp_path)

    try:
        # Trigger exception
        1 / 0
    except ZeroDivisionError as exc:
        hurdle = classifier.classify_exception(
            exc=exc,
            file_path="buggy.py",
            line_number=2,
        )

    assert hurdle.error_type == "ZeroDivisionError"
    assert "division by zero" in hurdle.message
    assert hurdle.file_path == "buggy.py"
    assert hurdle.line_number == 2
    assert len(hurdle.code_context) > 0
    assert "return 1 / 0" in hurdle.code_context[1]