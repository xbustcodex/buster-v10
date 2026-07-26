import sys
from pathlib import Path
import pytest

from buster.runtime.core import BusterRuntimeCore


def test_runtime_handles_hurdle_and_dispatches_events(tmp_path):
    module_file = tmp_path / "broken_logic.py"
    module_file.write_text("def run():\n    return 0\n", encoding="utf-8")

    test_file = tmp_path / "test_broken_logic.py"
    test_file.write_text(
        "from broken_logic import run\n"
        "def test_run():\n"
        "    assert run() == 1\n",
        encoding="utf-8",
    )

    core = BusterRuntimeCore(root=tmp_path)

    events = []
    core.dispatcher.subscribe("hurdle.resolved", lambda e: events.append(e))
    core.dispatcher.subscribe("hurdle.failed", lambda e: events.append(e))

    try:
        raise ValueError("Simulated runtime error in broken_logic")
    except Exception as exc:
        result = core.handle_hurdle_exception(
            exc=exc,
            replacement_code="def run():\n    return 1\n",
            test_command=[sys.executable, "-m", "pytest", "test_broken_logic.py"],
            file_path="broken_logic.py",
            line_number=2,
        )

    assert result.applied is True
    assert len(events) == 1
    
    payload = events[0].get("payload", events[0]) if isinstance(events[0], dict) else getattr(events[0], "payload", events[0])
    assert payload["applied"] is True
    assert payload["target_path"] == "broken_logic.py"