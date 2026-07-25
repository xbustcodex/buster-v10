"""
Test v14.2: Real-Time Event Feed Broadcaster
"""
import pytest
from buster.api.events import EventBroadcaster
from buster.autonomy.goals.idle_brain import IdleBrain


def test_event_broadcaster_pub_sub():
    broadcaster = EventBroadcaster()
    received_events = []

    def handle_event(payload):
        received_events.append(payload)

    broadcaster.subscribe(handle_event)

    # Broadcast Idle Brain state change
    brain = IdleBrain()
    new_state = brain.evaluate_next_state(active_tasks_count=0)

    broadcaster.publish("brain_state_change", {"state": new_state.value, "tick": brain.tick_count})

    assert len(received_events) == 1
    assert received_events[0]["event_type"] == "brain_state_change"
    assert received_events[0]["data"]["state"] == "OBSERVING"

    # Test unsubscribe
    broadcaster.unsubscribe(handle_event)
    broadcaster.publish("brain_state_change", {"state": "WAITING"})
    assert len(received_events) == 1  # No new events received