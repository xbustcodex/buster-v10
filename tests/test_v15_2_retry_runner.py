"""
Test v15.2: Automated Fallback & Retry Strategy Runner
"""
import pytest
from buster.autonomy.recovery.retry_runner import ResilientExecutionRunner


def test_retry_success_on_transient_error():
    attempts_count = 0

    def flaky_func():
        nonlocal attempts_count
        attempts_count += 1
        if attempts_count < 3:
            raise TimeoutError("Temporary network hiccup")
        return "SUCCESS_DATA"

    runner = ResilientExecutionRunner(max_retries=3, backoff_factor=0.01)
    res = runner.execute_with_retry(flaky_func)

    assert res["status"] == "success"
    assert res["attempts"] == 3
    assert res["result"] == "SUCCESS_DATA"
    assert res["fallback_used"] is False


def test_fallback_on_non_retryable_error():
    def failing_func():
        raise FileNotFoundError("Missing target payload file")

    def fallback_func():
        return "FALLBACK_DATA"

    runner = ResilientExecutionRunner(max_retries=3, backoff_factor=0.01)
    res = runner.execute_with_retry(failing_func, fallback_fn=fallback_func)

    assert res["status"] == "success"
    assert res["fallback_used"] is True
    assert res["result"] == "FALLBACK_DATA"
    assert res["attempts"] == 1