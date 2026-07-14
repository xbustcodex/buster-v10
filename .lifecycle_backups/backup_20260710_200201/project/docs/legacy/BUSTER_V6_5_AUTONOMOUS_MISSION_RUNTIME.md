# Buster v6.5 Autonomous Mission Runtime

This release gives Buster long-running mission management.

## Adds

- Mission model
- Mission steps
- Capability Registry
- Mission Scheduler
- Mission Executor
- AutonomousMissionRuntime
- Mission dashboard/widget

## Goal

Buster should be able to manage a development mission end-to-end:

```text
Plan
Load context
Build
Test
Fix
Review
Verify
Learn
```

Each step is assigned through the capability registry so future plugins can provide new skills without hard-coding the planner.
