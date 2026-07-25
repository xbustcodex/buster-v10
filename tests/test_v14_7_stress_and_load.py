"""
Test v14.7: Concurrent Load & Tick Stress Testing
"""
import concurrent.futures
import pytest
from buster.api.events import EventBroadcaster
from buster.autonomy.goals.idle_brain import IdleBrain
from buster.autonomy.goals.models import GoalProposal
from buster.autonomy.goals.registry import GoalRegistry
from buster.autonomy.goals.storage import GoalStorage


def test_concurrent_goal_registration_and_ticks(tmp_path):
    storage_path = tmp_path / "goals_registry.json"
    registry = GoalRegistry(storage=GoalStorage(storage_path=storage_path))
    brain = IdleBrain(registry=registry)
    broadcaster = EventBroadcaster()

    events_captured = []
    broadcaster.subscribe(lambda e: events_captured.append(e))

    def register_worker(worker_id: int):
        for i in range(10):
            prop = GoalProposal(
                title=f"Concurrent Goal {worker_id}-{i}",
                request="Stress test execution",
                target=f"/tmp/file_{worker_id}_{i}",
                signal_id=f"sig_{worker_id}_{i}",
            )
            registry.register_proposal(prop, evidence={"worker": worker_id})

            # Simulate state tick
            state = brain.evaluate_next_state(active_tasks_count=i)
            broadcaster.publish("brain_tick", {"state": state.value, "worker": worker_id})

    # Run 5 concurrent threads executing 10 goal registrations & ticks each (50 total)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(register_worker, w) for w in range(5)]
        
        # Unwrap thread exceptions so pytest reports the exact worker failure
        for future in concurrent.futures.as_completed(futures):
            future.result()

    # Verify state consistency across threads
    all_goals = registry.all_goals()
    assert len(all_goals) == 50
    assert len(events_captured) == 50