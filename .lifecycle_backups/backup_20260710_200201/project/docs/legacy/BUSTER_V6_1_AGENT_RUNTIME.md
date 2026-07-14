# Buster v6.1 Agent Runtime & Living Companion Core

This release turns the v6 SDK into a living agent platform.

## Adds

- Agent OS package
- AgentService model
- AgentRegistry
- AgentRuntime
- LivingCompanionRuntime
- Agent OS dashboard model
- Agent OS widget model
- Developer Mode scripts

## Developer workflow

Use:

```bat
scripts\test_push.bat "v6.1 agent runtime living companion"
```

This runs pytest first. It only commits and pushes if tests pass.

## Vision

Buster should feel like this while coding:

```text
09:12 Good morning Adam.
09:15 I noticed Android Studio is open.
09:18 The ESP32 project you worked on yesterday is available.
09:24 The Builder Agent finished compiling.
09:24 The Tester found one regression.
09:25 The issue was a missing import. It's repaired locally.
09:26 All tests are now passing.
09:26 I've recorded a new build strategy.
```
