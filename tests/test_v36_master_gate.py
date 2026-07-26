# tests/test_v36_master_gate.py
import pytest
from buster.security.master_gate import MasterControllerSecurityGate


def test_master_gate_signature_and_revocation():
    secret = b"master_deployment_secret_key"
    gate = MasterControllerSecurityGate(secret)

    code = "def secure_worker(): return 'OK'"
    sig = gate.generate_component_signature(code)

    # Verify valid signature
    assert gate.verify_component("worker_1", code, sig) is True

    # Verify tampered code fails validation
    tampered_code = "def secure_worker(): return 'COMPROMISED'"
    assert gate.verify_component("worker_1", tampered_code, sig) is False

    # Revoke component and check execution block
    gate.revoke_component("worker_1")
    assert gate.verify_component("worker_1", code, sig) is False

    with pytest.raises(PermissionError):
        gate.execute_under_master_supervision("worker_1", lambda: "should not run")