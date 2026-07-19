from __future__ import annotations

"""
Self-improvement UI package for Buster Desktop AI OS.

The package uses lazy imports so individual widgets can be added and tested
one at a time without breaking package imports while development is in progress.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    "SelfImprovementPanel",
    "FindingsTable",
    "JobQueue",
    "ExecutionCard",
    "HistoryPanel",
    "ModeSelector",
]

_EXPORTS = {
    "SelfImprovementPanel": (
        ".self_improvement_panel",
        "SelfImprovementPanel",
    ),
    "FindingsTable": (
        ".findings_table",
        "FindingsTable",
    ),
    "JobQueue": (
        ".job_queue",
        "JobQueue",
    ),
    "ExecutionCard": (
        ".execution_card",
        "ExecutionCard",
    ),
    "HistoryPanel": (
        ".history_panel",
        "HistoryPanel",
    ),
    "ModeSelector": (
        ".mode_selector",
        "ModeSelector",
    ),
}


if TYPE_CHECKING:
    from .execution_card import ExecutionCard
    from .findings_table import FindingsTable
    from .history_panel import HistoryPanel
    from .job_queue import JobQueue
    from .mode_selector import ModeSelector
    from .self_improvement_panel import SelfImprovementPanel


def __getattr__(name: str) -> Any:
    """
    Load exported widgets only when they are first accessed.

    This keeps the package importable while its modules are being introduced
    one at a time.
    """
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )

    module_name, attribute_name = target
    module = import_module(
        module_name,
        package=__name__,
    )
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(
        set(globals()) | set(__all__)
    )
