# Buster v11 Kernel Migration Contract

This document is the permanent architecture contract for the remainder of the
Buster v11 migration. Subsystem reports may record local implementation and
verification evidence, but they must not redefine these rules.

Architecture migration status is distinct from release acceptance. Every
version is additionally governed by the permanent
[Buster Release Gate](RELEASE_GATE.md). A subsystem may be migration-complete
while remaining `FAIL — Unverified` for release readiness.

## Source of truth

The existing Buster architecture and its working capabilities are the source
of truth. Migration centralizes ownership under the application-owned
`KernelRuntimeCore`; it does not redesign Buster, create parallel capability,
or collapse distinct cognitive responsibilities.

```text
main.py
  -> BusterRuntime
  -> V9MainWindow
  -> create_runtime_core()
  -> KernelRuntimeCore
  -> BusterKernel
```

There is one application runtime and one authoritative owner for each
capability. Kernel services may expose public commands, public events,
read-only detached `snapshot()` results, and domain-specific query methods.
They must not expose persistence internals, raw data paths, database handles,
or mutable internal state.

## Permanent panel architecture rule

Every V9 panel is a presentation boundary. A panel observes the runtime and
issues user requests; it never owns authoritative system state.

```text
User action
  -> Panel
  -> Canonical runtime service
  -> KernelRuntimeCore
  -> Authoritative state
  -> Public event or detached snapshot
  -> Panel refresh
```

Panels must not bypass this flow.

### Permitted panel responsibilities

A panel may:

- display detached snapshots;
- issue public service commands;
- subscribe to public events;
- maintain transient presentation state;
- manage presentation-only timers;
- render progress and errors;
- manage layouts and widgets.

### Prohibited panel ownership

A panel must not own or construct:

- business logic or authoritative runtime state;
- persistence or direct filesystem access;
- backend workers, schedulers, registries, or queues;
- runtimes, dispatchers, event routers, or service containers;
- AI providers or orchestration infrastructure;
- security policy;
- knowledge, world-model, or memory state.

The application-owned `KernelRuntimeCore` must be injected into the panel by
the V9 composition root. A panel must never call `create_runtime_core()` or
construct a replacement backend.

## Panel compatibility rule

Registry-backed canonical service resolution is preferred. Direct runtime
attributes and legacy paths may remain only while a proven active consumer
requires them.

Every retained compatibility fallback must record:

1. the active consumer;
2. the reason the fallback is still required;
3. the verification protecting its behavior;
4. the planned retirement boundary.

Compatibility is temporary. Once no active runtime, panel, test, import, or
persistence contract requires a fallback, it must be removed from active use
and quarantined before permanent deletion.

## Panel verification contract

A panel migration is complete only when evidence proves that the panel:

- receives the single application-owned `KernelRuntimeCore`;
- resolves authoritative services through the kernel registry;
- constructs no authoritative backend objects;
- performs no direct persistence access;
- exposes no mutable runtime state;
- preserves existing public behavior, signals, events, payloads, and layout;
- disconnects every public event subscription cleanly;
- stops every presentation timer cleanly;
- survives repeated open and close cycles;
- shuts down cleanly with the application.

Required verification includes source inspection, focused static validation,
focused automated tests where the environment permits them, registry and
identity checks, and manual Buster startup/panel/shutdown verification. A
blocked full-runtime test must be reported as unavailable rather than passed.

## Standard migration sequence

```text
Inspect implementations and consumers
  -> Identify the authoritative implementation
  -> Audit persistence and background activity
  -> Establish one KernelRuntimeCore-owned instance
  -> Register one canonical service
  -> Preserve proven compatibility
  -> Expose public commands, events, snapshots, and queries
  -> Verify identity, lifecycle, construction count, and compatibility
  -> Verify panel/Brain discovery where applicable
  -> Stop before beginning the next bounded subsystem
```

The kernel owns instances, not all responsibilities. Specialized services such
as Memory, World Model, Skills, Learning, Dream, Consolidation, Conversation,
Self-Improvement, and Security retain their distinct domains.

## Canonical remaining order

1. Finish remaining panel migration.
2. Knowledge Orchestrator Runtime Boundary.
3. Conversation Lifecycle Runtime Boundary.
4. Technical Conversation Engine.
5. Memory Retrieval Runtime Boundary.
6. Legacy retirement, quarantine, and dead-code audit.
7. Full repository regression.
8. Packaging and executable verification.
9. Buster Prime Fleet architecture.
10. Federation Security Runtime Boundary (S2).

Legacy quarantine remains deferred until the remaining panels and intelligence
boundaries pass broad regression and prove their compatibility paths dead.

## Buster and Buster Prime authority

Buster owns and controls its installed environment, data, permissions,
security decisions, and application of updates.

Buster Prime may coordinate signed and verified fleet intelligence, security
advisories, learning packages, and patch packages. It must never bypass a
receiving Buster's local policy or owner approval. Federation must not provide
remote shell control, unrestricted filesystem access, raw memory copying, or
automatic unapproved installation.

The permanent principle is:

```text
The runtime owns the system.
The panels own the presentation.
Each Buster remains its own final authority.
```
