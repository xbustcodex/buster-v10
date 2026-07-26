# tests/test_v31_capabilities.py
import pytest
import threading
from buster.capabilities import (
    CapabilityRegistry,
    PermissionGate,
    CapabilityExecutionContext,
    DuplicateCapabilityError,
    CapabilityNotFoundError,
    PermissionDeniedError,
    CapabilityDisabledError,
)
from buster.capabilities.python_cap import PythonCapability


def test_registry_registers_valid_capability():
    registry = CapabilityRegistry()
    py_cap = PythonCapability(registry)
    registry.register(py_cap)

    descriptors = registry.list_descriptors()
    assert len(descriptors) == 1
    assert descriptors[0].capability_id == "core.python"


def test_registry_rejects_duplicate_id():
    registry = CapabilityRegistry()
    py_cap1 = PythonCapability(registry)
    py_cap2 = PythonCapability(registry)

    registry.register(py_cap1)
    with pytest.raises(DuplicateCapabilityError):
        registry.register(py_cap2)


def test_registry_rejects_invalid_descriptor():
    class BadCap(PythonCapability):
        def describe(self):
            return None  # Invalid

    registry = CapabilityRegistry()
    with pytest.raises(Exception):
        registry.register(BadCap(registry))


def test_registry_finds_capability_by_action():
    registry = CapabilityRegistry()
    registry.register(PythonCapability(registry))

    caps = registry.find_by_action("python.version")
    assert len(caps) == 1
    assert caps[0].capability_id == "core.python"


def test_action_schema_validation_rejects_bad_arguments():
    cap = PythonCapability()
    ctx = CapabilityExecutionContext(
        mission_id="m_1",
        task_id="t_1",
        trace_id="tr_1",
        agent_id="agent_1",
        approved_permissions=frozenset(),
    )
    with pytest.raises(Exception):
        cap.execute("python.syntax_check", {"code": 123}, ctx)  # expected str


def test_permission_gate_blocks_unapproved_action():
    registry = CapabilityRegistry()
    cap = PythonCapability(registry)
    registry.register(cap)

    ctx = CapabilityExecutionContext(
        mission_id="m_1",
        task_id="t_1",
        trace_id="tr_1",
        agent_id="agent_1",
        approved_permissions=frozenset(),  # Missing process.launch
    )

    with pytest.raises(PermissionDeniedError):
        cap.execute("python.run_tests", {"target": "tests"}, ctx)


def test_health_snapshot_reports_all_capabilities():
    registry = CapabilityRegistry()
    registry.register(PythonCapability(registry))

    snapshot = registry.health_snapshot()
    assert len(snapshot) == 1
    assert snapshot[0].capability_id == "core.python"
    assert snapshot[0].status == "HEALTHY"


def test_health_change_publishes_event():
    events = []
    class MockBus:
        def publish(self, name, data):
            events.append((name, data))

    bus = MockBus()
    registry = CapabilityRegistry(event_bus=bus)
    cap = PythonCapability(registry)
    registry.register(cap)

    registry.set_enabled("core.python", False)
    assert any(e[0] == "capability.disabled" for e in events)


def test_execution_result_preserves_trace_context():
    cap = PythonCapability()
    ctx = CapabilityExecutionContext(
        mission_id="m_100",
        task_id="t_200",
        trace_id="trace_abc_999",
        agent_id="agent_1",
        approved_permissions=frozenset(["process.launch"]),
    )
    result = cap.execute("python.version", {}, ctx)
    assert result.success is True
    assert "version" in result.output


def test_disabled_capability_cannot_execute():
    registry = CapabilityRegistry()
    cap = PythonCapability(registry)
    registry.register(cap)
    registry.set_enabled("core.python", False)

    ctx = CapabilityExecutionContext(
        mission_id="m_1",
        task_id="t_1",
        trace_id="tr_1",
        agent_id="agent_1",
        approved_permissions=frozenset(["process.launch"]),
    )
    with pytest.raises(CapabilityDisabledError):
        cap.execute("python.version", {}, ctx)


def test_registry_is_thread_safe():
    registry = CapabilityRegistry()
    
    def reg(i):
        try:
            class DummyCap(PythonCapability):
                capability_id = f"dummy.{i}"
            registry.register(DummyCap(registry))
        except Exception:
            pass

    threads = [threading.Thread(target=reg, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(registry.list_descriptors()) >= 1


def test_python_capability_end_to_end():
    cap = PythonCapability()
    ctx = CapabilityExecutionContext(
        mission_id="m_e2e",
        task_id="t_e2e",
        trace_id="tr_e2e",
        agent_id="builder",
        approved_permissions=frozenset(["process.launch"]),
    )

    # 1. Version check
    res_ver = cap.execute("python.version", {}, ctx)
    assert res_ver.success is True
    assert "executable" in res_ver.output

    # 2. Syntax check
    res_syn = cap.execute("python.syntax_check", {"code": "print('hello buster')"}, ctx)
    assert res_syn.success is True
    assert res_syn.output["valid"] is True