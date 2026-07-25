"""
Test v13.7: Idle Brain State Machine
"""
import pytest
from buster.autonomy.goals.idle_brain import BrainState, IdleBrain


def test_idle_brain_state_rotation():
    brain = IdleBrain()

    # When active tasks exist, brain remains in WAITING state
    assert brain.evaluate_next_state(active_tasks_count=2) == BrainState.WAITING

    # Idle tick rotation: OBSERVING -> SCANNING -> THINKING
    assert brain.evaluate_next_state(active_tasks_count=0) == BrainState.OBSERVING
    assert brain.evaluate_next_state(active_tasks_count=0) == BrainState.SCANNING
    assert brain.evaluate_next_state(active_tasks_count=0) == BrainState.THINKING
    assert brain.evaluate_next_state(active_tasks_count=0) == BrainState.OBSERVING