"""
Test v15.3: Self-Healing Circuit Breaker
"""
import time
import pytest
from buster.autonomy.recovery.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException


def test_circuit_breaker_tripping():
    cb = CircuitBreaker(max_failures=2, reset_timeout=0.2)
    target = "/tmp/failing_target"

    # Initial state should be CLOSED
    assert cb.get_state(target) == "CLOSED"
    assert cb.check_allow_execution(target) is True

    # First failure
    cb.record_failure(target)
    assert cb.get_state(target) == "CLOSED"

    # Second failure -> should trip to OPEN
    cb.record_failure(target)
    assert cb.get_state(target) == "OPEN"

    with pytest.raises(CircuitBreakerOpenException):
        cb.check_allow_execution(target)


def test_circuit_breaker_reset():
    cb = CircuitBreaker(max_failures=1, reset_timeout=0.1)
    target = "/tmp/reset_target"

    cb.record_failure(target)
    assert cb.get_state(target) == "OPEN"

    # Wait for reset timeout
    time.sleep(0.15)
    assert cb.get_state(target) == "HALF_OPEN"

    # Successful run resets state back to CLOSED
    cb.record_success(target)
    assert cb.get_state(target) == "CLOSED"