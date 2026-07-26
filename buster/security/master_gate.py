# buster/security/master_gate.py
from __future__ import annotations

import hmac
import hashlib
from typing import Dict, Any, Callable


class MasterControllerSecurityGate:
    """Centralized master authorization and tamper-prevention gateway for full version rollouts."""

    def __init__(self, master_secret_key: bytes) -> None:
        self.master_secret_key = master_secret_key
        self._revoked_components: set[str] = set()

    def generate_component_signature(self, component_code: str) -> str:
        """Generates an HMAC-SHA256 master signature for a component or module."""
        return hmac.new(
            self.master_secret_key,
            component_code.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def verify_component(self, component_id: str, component_code: str, provided_signature: str) -> bool:
        """Verifies if a component's code matches its master signature and is not revoked."""
        if component_id in self._revoked_components:
            return False

        expected_signature = self.generate_component_signature(component_code)
        return hmac.compare_digest(expected_signature, provided_signature)

    def revoke_component(self, component_id: str) -> None:
        """Immediately revokes a compromised component from the execution ecosystem."""
        self._revoked_components.add(component_id)

    def execute_under_master_supervision(self, component_id: str, action: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executes a subordinated action only if the component is active and unrevoked."""
        if component_id in self._revoked_components:
            raise PermissionError(f"Security Alert: Component '{component_id}' has been revoked due to suspected tampering.")
        return action(*args, **kwargs)