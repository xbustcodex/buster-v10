# Buster Agent Operating System – Control Plane

## The Boundary Line Is Drawn

This milestone establishes the architectural boundary between the **Control Plane** and the **Execution Plane**.

## Control Plane (`buster/kernel/`)

The Control Plane is responsible for runtime coordination and system governance. Its purpose is to remain stable, predictable, and independent of higher-level AI behavior.

### Responsibilities

- Runtime lifecycle orchestration
- Event routing
- Permission and policy enforcement
- World state management
- Task scheduling
- Agent lifecycle management
- Audit and integrity verification

The Control Plane does **not** contain AI reasoning, planning logic, or domain-specific intelligence.

---

## Execution Plane (`agents/` and `services/`)

All future intelligence is implemented outside the kernel.

### Agents

Goal-oriented, transient workers responsible for autonomous execution.

Examples:

- Builder Agent
- Tester Agent
- Fixer Agent
- Reviewer Agent
- Verifier Agent

### Services

Long-running background capabilities that provide infrastructure for the runtime.

Examples:

- Voice
- Vision
- Memory
- Git
- Plugins
- Updates

Services expose capabilities.

Agents consume those capabilities.

The kernel coordinates both without embedding their implementation logic.

---

## Architectural Principle

> **Keep `core.py` small, stable, and boring.**

`core.py` exists only to coordinate the runtime.

It should never accumulate planning logic, AI decision-making, project-specific behavior, or business rules.

Every new capability should be implemented by extending the surrounding modules rather than expanding the orchestrator.

---

## Layer Responsibilities

```text
Application Intelligence
│
├── Agents
├── Services
│
└───────────────┐
                │
        Buster Control Plane
                │
    ┌─────────────────────────────┐
    │ core.py                     │
    │ event_router.py             │
    │ permissions.py              │
    │ world_model.py              │
    │ scheduler.py                │
    │ agent_manager.py            │
    │ audit.py                    │
    └─────────────────────────────┘
                │
          Windows Operating System
                │
             Hardware
```

---

## Runtime Responsibilities

### `core.py`
- Runtime lifecycle orchestration
- Service initialization
- Kernel state transitions
- Coordination of control-plane modules

### `event_router.py`
- Topic-based message routing
- Decoupled inter-module communication
- Event delivery

### `permissions.py`
- RBAC capability matrix
- Policy enforcement
- Authorization checks

### `world_model.py`
- System reality model
- Environment telemetry
- Runtime context
- Project state

### `scheduler.py`
- Priority task pipeline
- Async execution queue
- Work scheduling

### `agent_manager.py`
- Agent registration
- Worker lifecycle
- Agent supervision

### `audit.py`
- Tamper-evident, hash-chained audit ledger
- Canonical serialization
- Thread-safe append operations
- Ledger integrity verification
- Chain recovery after restart
- Truncation detection using checkpoints

---

## Security Guarantees

- Deterministic SHA-256 record hashing
- Hash-chained audit records
- Canonical JSON serialization
- Thread-safe writes
- Ledger continuity across restarts
- Truncation detection
- Full integrity verification

### Non-Goals

- Data encryption
- Digital signatures
- Distributed consensus
- Remote replication

---

## Long-Term Rule

The Control Plane should evolve slowly and only when fundamental runtime responsibilities change.

Most future development should occur in:

- New agents
- New services
- New plugins
- Planning improvements
- Richer world models
- Expanded automation

—not inside the kernel itself.

---

## Design Philosophy

The kernel is intentionally **boring**.

It should remain predictable, deterministic, and easy to reason about.

Complexity belongs above the Control Plane, where autonomous agents and services can evolve independently without destabilizing the runtime.

This separation allows Buster to scale while preserving a stable foundation.

---

## Milestone Achieved

Buster is no longer architected as a conventional desktop AI application.

It is now structured as an **Agent Operating System** with a clearly defined **Control Plane** responsible for coordination, governance, runtime stability, and integrity, while autonomous behavior resides in independently evolving execution components.
