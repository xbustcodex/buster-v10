"""
Test v15.1: Execution Error Diagnostics & Classification
"""
import pytest
from buster.autonomy.recovery.diagnostics import ErrorCategory, ErrorDiagnostic


def test_classify_transient_error():
    exc = TimeoutError("Connection timed out waiting for service")
    diag = ErrorDiagnostic.classify_exception(exc)

    assert diag["category"] == ErrorCategory.TRANSIENT.value
    assert diag["retryable"] is True


def test_classify_missing_resource():
    exc = FileNotFoundError("No such file or directory: 'config.json'")
    diag = ErrorDiagnostic.classify_exception(exc)

    assert diag["category"] == ErrorCategory.MISSING_RESOURCE.value
    assert diag["retryable"] is False


def test_classify_permission_error():
    exc = PermissionError("Permission denied accessing /root/secret")
    diag = ErrorDiagnostic.classify_exception(exc)

    assert diag["category"] == ErrorCategory.PERMISSION.value
    assert diag["retryable"] is False