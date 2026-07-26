# tests/test_v30_observation.py
import pytest
from buster.autonomy.observation_engine import ObservationEngine, Observation


def test_observation_engine_creation_and_filtering():
    engine = ObservationEngine(importance_threshold=0.5)

    # High importance event
    obs1 = engine.create_observation(
        mission_id="mission_01",
        source="tester",
        obs_type="test.failed",
        importance=0.91,
        requires_replan=True,
        payload={"error": "AssertionError"},
    )

    # Low importance noise event
    obs2 = engine.create_observation(
        mission_id="mission_01",
        source="telemetry",
        obs_type="heartbeat.tick",
        importance=0.10,
        requires_replan=False,
    )

    all_obs = [obs1, obs2]
    filtered = engine.filter_observations(all_obs)

    assert len(filtered) == 1
    assert filtered[0].observation_id == obs1.observation_id
    assert filtered[0].type == "test.failed"