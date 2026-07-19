from __future__ import annotations

"""
Compatibility forwarding module.

The repair planner worker is implemented at:

    buster.autonomy.repair_plan_worker

The Self Improvement panel still imports it from:

    buster.ui.v9.panels.self_improvement.repair_plan_worker
"""

from buster.autonomy.repair_plan_worker import *  # noqa: F401,F403
