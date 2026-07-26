from datetime import datetime
from pathlib import Path
import pytest

from buster.runtime.core import BusterRuntimeCore


def test_runtime_tick_executes_curiosity_exploration(tmp_path):
    # Setup candidate file with high complexity line count
    sample_file = tmp_path / "heavy_module.py"
    sample_file.write_text("\n".join([f"x = {i}" for i in range(300)]), encoding="utf-8")

    core = BusterRuntimeCore(root=tmp_path)

    events = []
    core.dispatcher.subscribe("curiosity.exploration_completed", lambda e: events.append(e))

    # Target Monday 10:00 AM (WORK state)
    work_time = datetime(2026, 7, 20, 10, 0, 0)
    core.tick(now=work_time)

    assert len(events) == 1
    # Check payload structure returned by EventDispatcher
    payload = events[0].get("payload", events[0]) if isinstance(events[0], dict) else getattr(events[0], "payload", events[0])
    assert payload["target_path"].endswith("heavy_module.py")
    assert payload["success"] is True