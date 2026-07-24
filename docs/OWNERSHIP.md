# Buster OS — Subsystem Ownership & Architecture Map

This document establishes the canonical domain boundaries, responsibilities, and allowed dependency flows across the Buster platform.

---

## 1. Dependency Hierarchy Rules

Dependencies **must strictly flow downwards**:

$$\text{UI} \longrightarrow \text{SDK / Runtime} \longrightarrow \text{Subsystems} \longrightarrow \text{Kernel}$$

- **UI (`ui/`)**: Can import `runtime` and `sdk`. Must never be imported by core engines.
- **Runtime (`runtime/`)**: Coordinates lifecycle and services. Imports subsystems and `kernel`.
- **Subsystems (`brain/`, `mind/`, `automation/`, `learning/`, `experience/`)**: Handle domain-specific intelligence and routines. Import `kernel`.
- **Kernel (`kernel/`)**: Base OS primitives, event dispatching, and core protocols. Python stdlib & non-domain external libraries only.

---

## 2. Package Ownership Matrix

| Package | Domain Responsibility | Canonical Entry Points / Primary Exports |
| :--- | :--- | :--- |
| `kernel/` | Low-level event loop, base event bus, atomic file storage, protocols, repair primitives | `EventBus`, core state models, base protocols |
| `brain/` | Cognition, LLM provider routing, long-term reasoning, prompt management | `AIProviderManager`, model providers |
| `mind/` | Perception parsing, vision stream ingestion, environmental presence | Vision/Presence workers & perception models |
| `automation/` | OS-level action execution, command runners, local automation scripts | Scripting engine, execution handlers |
| `learning/` & `experience/` | Post-execution analysis, skill acquisition, XP tracking, evolution state | `EvolutionState`, `ExperienceEngine` |
| `autonomy/` | Mission loops, self-improvement cycles, background execution engines | `AutonomyEngine`, `ExecutionEngine`, `SelfImprovementService` |
| `runtime/` | System lifecycle, service registry, state snapshotting, developer tools | `BusterRuntimeCore`, `create_runtime_core` |
| `sdk/` | Extension interfaces, public capability contracts, plugin host API | `build_sdk_runtime`, Service Registry accessors |
| `ui/` | Qt interface, dashboards, real-time telemetry, settings, user controls | `DashboardWindow`, `SettingsPanel`, UI widgets |

---

## 3. Subsystem Lifecycle & Startup

All permanent background services are instantiated and managed directly by `BusterRuntimeCore` (`buster/runtime/core.py`).

```python
# Canonical startup
runtime = create_runtime_core(root=".")
runtime.start()

# Canonical teardown
runtime.stop()