"""Buster Jarvis Autonomy Layer.

This package lets Buster recommend next actions, remember autonomous
sessions, and expose OS-style status snapshots to the dashboard.
"""

from .engine import AutonomyEngine
from .next_actions import NextActionRecommender
from .records import AutonomyJob, AutonomyDecision
from .dashboard import AutonomyDashboard

__all__ = [
    "AutonomyEngine",
    "NextActionRecommender",
    "AutonomyJob",
    "AutonomyDecision",
    "AutonomyDashboard",
]
