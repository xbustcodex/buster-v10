# buster/capabilities/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple


@dataclass(frozen=True, slots=True)
class ActionDescriptor:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_permissions: Tuple[str, ...] = ()
    reversible: bool = False
    timeout_seconds: float = 30.0
    risk_level: str = "low"


@dataclass(frozen=True, slots=True)
class ResourceRequirements:
    cpu_cores: float = 0.5
    memory_mb: int = 256
    requires_network: bool = False
    requires_gpu: bool = False
    requires_filesystem: bool = False


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    capability_id: str
    name: str
    version: str
    description: str
    actions: Tuple[ActionDescriptor, ...]
    required_permissions: Tuple[str, ...]
    resource_requirements: ResourceRequirements
    provider: str = "buster"
    tags: Tuple[str, ...] = ()
    enabled_by_default: bool = True


@dataclass(frozen=True, slots=True)
class CapabilityHealth:
    capability_id: str
    status: str  # HEALTHY, DEGRADED, UNAVAILABLE, DISABLED
    checked_at: str
    latency_ms: Optional[float] = None
    message: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CapabilityExecutionContext:
    mission_id: str
    task_id: str
    trace_id: str
    agent_id: str
    workspace_id: Optional[str] = None
    approved_permissions: FrozenSet[str] = field(default_factory=frozenset)
    timeout_seconds: Optional[float] = None


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    success: bool
    capability_id: str
    action: str
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)