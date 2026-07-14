# Buster AI Companion OS v6 Foundation

v6 starts with a stable SDK and runtime foundation.

## Core rule

Plugins and subsystems should use the SDK instead of reaching into internal modules directly.

```python
sdk.observe(...)
sdk.publish(...)
sdk.subscribe(...)
sdk.speak(...)
sdk.learn(...)
sdk.create_goal(...)
sdk.register_service(...)
sdk.register_module(...)
```

## Git workflow

Use this after source changes:

```bat
scripts\test_push.bat "your commit message"
```

It runs pytest first. It only commits and pushes if tests pass.

## What this adds

- Buster SDK
- Unified event API
- Service registry
- Module lifecycle
- Safe config layer
- v6 foundation runtime
- test-and-push workflow

## Why

Buster is now large enough that new systems need a stable internal API.

The SDK protects the architecture from becoming tightly coupled.
