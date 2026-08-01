# Buster Release Gate

## Status and scope

Status: **Accepted — permanent release policy**

Scope: Every Buster version, including v11, v12, and later releases.

This policy governs release readiness independently of architecture migration,
implementation progress, unit tests, and migration-ledger status.

## Zero Assumption Principle

The default state of every feature, workflow, panel, subsystem, and visible
control is:

```text
FAIL — Unverified
```

Nothing earns `PASS` because it exists, compiles, opens, is registered, or
appears correctly wired. `PASS` must be earned through real end-to-end use in
the running application.

## What does not prove completion

A feature is not complete merely because:

- its code compiles;
- unit, integration, or source-level tests pass;
- its panel opens;
- its controls are visible;
- a signal is connected;
- a backend command exists;
- a service is registered;
- the workflow appears theoretically correct.

These are supporting evidence only. They never replace manual functional
acceptance.

## Evidence required for PASS

A real user must complete the feature's intended workflow through the actual
Buster UI. Evidence must prove all applicable stages:

1. The UI interaction works through the normal user path.
2. The request reaches the correct canonical runtime service.
3. The authoritative backend executes the intended operation.
4. Required state transitions occur exactly once.
5. Canonical events and audit evidence are emitted correctly.
6. The UI updates truthfully from events, snapshots, or public queries.
7. Invalid input, unavailable services, permission denial, approval denial,
   execution failure, and cancellation are handled correctly where applicable.
8. Required state persists and reloads correctly.
9. Repeated execution is idempotent or rejected safely.
10. Startup succeeds in the supported production environment.
11. Panel close/reopen and application shutdown succeed.
12. No worker, timer, subscription, process, server, port, device, or window
    leaks.

If any required stage is untested or fails, the item remains `FAIL` until it is
repaired and successfully retested.

## Acceptance states

Every item must have exactly one of these states:

| State | Meaning |
|---|---|
| `PASS` | Fully verified manually with recorded end-to-end evidence. |
| `FAIL — Unverified` | Default state; the complete workflow has not been manually exercised. |
| `FAIL — Defect Open` | Manually tested and a concrete defect remains. |
| `BLOCKED` | Manual verification cannot proceed because a proven architectural or environmental dependency is missing. |
| `NOT APPLICABLE` | The control or evidence category legitimately does not apply, with a recorded justification. |
| `REMOVED` | The control or capability was intentionally retired and is no longer reachable. |

There is no acceptance state for “probably works,” “looks correct,” “should
work,” or “tests passed.”

## Evidence record

Every acceptance record must identify:

- date and time tested;
- Buster version, build, and branch under test;
- tester identity, such as Codex, Adam, or both;
- test environment, including operating system, Python, PySide6, packaging form,
  and relevant hardware or device context;
- panel, page, control, and complete workflow;
- canonical service and backend command;
- temporary fixture or disposable data used;
- expected and observed state transitions;
- UI result and authoritative backend result;
- manual workflow evidence and screenshots or logs where applicable;
- related regression tests, if any;
- persistence evidence where applicable;
- success, error, denial, cancellation, and repeated-use evidence where
  applicable;
- close/reopen and shutdown result;
- resource observations;
- defect and correction reference when the item previously failed;
- final acceptance state.

No untested control may be marked `PASS`.

Every `FAIL — Defect Open` record must include the observed defect, exact
reproduction steps, expected behavior, and actual behavior. Every `BLOCKED`
record must name the specific architectural or environmental dependency that
prevents verification and include evidence that the dependency is genuinely
missing. A status label without this evidence is not a valid acceptance record.

## Completion milestones

Every subsystem progresses through three distinct milestones. None implies the
next milestone automatically.

### Migration Complete

The capability has been moved to the approved architecture with one
authoritative owner, canonical service resolution, preserved compatibility,
and appropriate automated verification.

### Acceptance Complete

Every reachable real-UI workflow for the subsystem has passed this Release
Gate. Every control is classified, every `PASS` has the required evidence, and
all applicable persistence, failure, repetition, close/reopen, and resource
checks have succeeded.

### Release Ready

The acceptance-complete subsystem is included in a complete Buster version
whose other reachable subsystems and version-level startup, shutdown,
regression, stability, and packaging checks also satisfy the Release Gate.

A capability may be `Migration Complete` while remaining
`FAIL — Unverified` for acceptance. It may also be `Acceptance Complete` while
the containing version is not yet `Release Ready`. Migration or subsystem
acceptance status must never be used as evidence that the whole release is
ready.

## Release rule

A Buster version is not releasable until:

- every reachable panel and child window is inventoried;
- every visible control is classified;
- every reachable workflow is manually exercised;
- every `PASS` has complete supporting evidence;
- every `FAIL — Defect Open` is fixed or explicitly accepted as a release
  blocker;
- every `BLOCKED` item has a proven dependency and release decision;
- every `NOT APPLICABLE` and `REMOVED` item is justified;
- repeated startup, open/close, and shutdown cycles remain clean;
- resource observations show no active canonical leaks.

Automated tests remain mandatory where defined, but they supplement rather
than replace this gate.

## Change policy

This is a permanent governing policy. Future releases may strengthen it but
must not silently weaken or bypass it. A deliberate policy change must be
recorded as an explicit architecture/release-governance decision rather than
being inferred from implementation or schedule pressure.
