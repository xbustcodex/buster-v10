# tests/test_v31_all_capabilities.py
import pytest
from buster.capabilities import CapabilityRegistry, CapabilityExecutionContext
from buster.capabilities.terminal_cap import TerminalCapability
from buster.capabilities.playwright_cap import PlaywrightCapability
from buster.capabilities.windows_cap import WindowsAutomationCapability
from buster.capabilities.android_cap import AndroidCapability
from buster.capabilities.esp32_cap import ESP32Capability


def test_all_capabilities_register_and_snapshot():
    registry = CapabilityRegistry()
    registry.register(TerminalCapability(registry))
    registry.register(PlaywrightCapability(registry))
    registry.register(WindowsAutomationCapability(registry))
    registry.register(AndroidCapability(registry))
    registry.register(ESP32Capability(registry))

    descriptors = registry.list_descriptors()
    assert len(descriptors) == 5

    snapshot = registry.health_snapshot()
    assert len(snapshot) == 5
    for h in snapshot:
        assert h.status in ("HEALTHY", "DEGRADED", "UNAVAILABLE", "DISABLED")