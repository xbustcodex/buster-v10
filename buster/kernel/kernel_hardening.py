"""
Buster Kernel v10.5 - Hardening & Integration Engine
Unifies AST Security, Subprocess Isolation, RBAC Permissions, Async Task Scheduling,
World Model Monitoring, Agent Lifecycle, and Hash-Chained Auditing.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import logging
import platform
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import psutil

logger = logging.getLogger("buster.kernel.hardening")

GENESIS_HASH = "GENESIS_HASH_00000000000000000000000000000000"


# ============================================================================
# 1. AST SECURITY INTERCEPT HARDENING
# ============================================================================

class ASTSecurityVisitor(ast.NodeVisitor):
    """AST Visitor detecting prohibited syntax nodes and dangerous function calls."""

    BLOCKED_FUNCTIONS = {"eval", "exec", "__import__", "compile", "breakpoint"}
    BLOCKED_MODULES = {"subprocess", "os.system", "shutil", "ctypes"}

    def __init__(self):
        self.violations: List[str] = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in self.BLOCKED_FUNCTIONS:
            self.violations.append(f"Blocked function call: '{node.func.id}' at line {node.lineno}")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in {"system", "popen", "spawn"}:
                self.violations.append(f"Blocked method execution: '{node.func.attr}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name in self.BLOCKED_MODULES:
                self.violations.append(f"Blocked import module: '{alias.name}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module in self.BLOCKED_MODULES:
            self.violations.append(f"Blocked import from module: '{node.module}' at line {node.lineno}")
        self.generic_visit(node)


class HardenedSecurityIntercept:
    """AST-driven security inspector and path boundary validator."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = (project_root or Path.cwd()).resolve()

    def validate_path(self, target_path: str | Path) -> Tuple[bool, str]:
        try:
            resolved = (self.project_root / target_path).resolve()
            if not str(resolved).startswith(str(self.project_root)):
                return False, f"Path traversal blocked: '{target_path}'"
            return True, "Path validated"
        except Exception as exc:
            return False, f"Invalid path: {exc}"

    def inspect_ast(self, code_content: str) -> Tuple[bool, List[str]]:
        try:
            tree = ast.parse(code_content)
            visitor = ASTSecurityVisitor()
            visitor.visit(tree)
            if visitor.violations:
                return False, visitor.violations
            return True, []
        except SyntaxError as syn_err:
            return False, [f"Syntax Error in payload: {syn_err}"]


# ============================================================================
# 2. ISOLATED SUBPROCESS SANDBOX
# ============================================================================

class HardenedSandboxManager:
    """Runs Python scripts in an isolated subprocess with explicit execution timeout."""

    def __init__(self, security_intercept: HardenedSecurityIntercept, timeout_sec: float = 10.0):
        self.security = security_intercept
        self.timeout_sec = timeout_sec

    def execute_code(self, code_content: str) -> Dict[str, Any]:
        is_safe, violations = self.security.inspect_ast(code_content)
        if not is_safe:
            return {"success": False, "output": "", "error": f"AST Security Violations: {violations}"}

        try:
            res = subprocess.run(
                [sys.executable, "-c", code_content],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )
            return {
                "success": res.returncode == 0,
                "output": res.stdout.strip(),
                "error": res.stderr.strip() if res.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": f"Execution timed out after {self.timeout_sec}s"}
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc)}


# ============================================================================
# 3. RBAC PERMISSION ENGINE
# ============================================================================

class PermissionScope(Enum):
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    TERMINAL_EXEC = "terminal:exec"
    GIT_COMMIT = "git:commit"
    SYSTEM_SHUTDOWN = "system:shutdown"
    SECRET_READ = "secret:read"
    SYSTEM_MODIFY = "system:modify"


class PermissionManager:
    """Capability-based security policy engine."""

    def __init__(self) -> None:
        self._role_permissions: Dict[str, Set[PermissionScope]] = {
            "admin": set(PermissionScope),
            "builder": {
                PermissionScope.FILE_READ,
                PermissionScope.FILE_WRITE,
                PermissionScope.TERMINAL_EXEC,
                PermissionScope.GIT_COMMIT,
            },
            "researcher": {PermissionScope.FILE_READ},
            "tester": {PermissionScope.FILE_READ, PermissionScope.TERMINAL_EXEC},
        }
        self._agent_roles: Dict[str, str] = {}

    def assign_role(self, agent_id: str, role: str) -> None:
        if role not in self._role_permissions:
            raise ValueError(f"Unknown role: {role}")
        self._agent_roles[agent_id] = role
        logger.info(f"Assigned role '{role}' to agent '{agent_id}'")

    def authorize(self, agent_id: str, scope: PermissionScope) -> bool:
        role = self._agent_roles.get(agent_id)
        if not role:
            logger.warning(f"Access Denied: Agent '{agent_id}' has no assigned role.")
            return False
        return scope in self._role_permissions.get(role, set())


# ============================================================================
# 4. ASYNC TASK SCHEDULER
# ============================================================================

class TaskPriority(Enum):
    LOW = 30
    NORMAL = 20
    HIGH = 10
    CRITICAL = 0


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass(order=True)
class KernelTask:
    priority: int
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    agent_id: str = field(compare=False)
    coro_func: Callable[..., Any] = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    result: Optional[Any] = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)


class TaskScheduler:
    """Async priority task runner."""

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[KernelTask] = asyncio.PriorityQueue()
        self._tasks: Dict[str, KernelTask] = {}
        self._worker_task: Optional[asyncio.Task] = None

    def schedule(
        self,
        name: str,
        agent_id: str,
        coro_func: Callable[..., Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        task_id = f"TSK-{uuid.uuid4().hex[:6]}"
        task = KernelTask(
            priority=priority.value,
            task_id=task_id,
            name=name,
            agent_id=agent_id,
            coro_func=coro_func,
        )
        self._tasks[task_id] = task
        self._queue.put_nowait(task)
        return task_id

    async def start(self) -> None:
        self._worker_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self) -> None:
        while True:
            task = await self._queue.get()
            task.status = TaskStatus.RUNNING
            try:
                task.result = await task.coro_func()
                task.status = TaskStatus.COMPLETED
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
            finally:
                self._queue.task_done()


# ============================================================================
# 5. WORLD MODEL & AGENT MANAGER
# ============================================================================

@dataclass
class SystemHardwareState:
    os_name: str = platform.system()
    os_version: str = platform.version()
    cpu_count: int = psutil.cpu_count(logical=True) or 1
    ram_gb: float = round(psutil.virtual_memory().total / (1024**3), 2)
    ram_usage_pct: float = 0.0

    def refresh(self) -> None:
        self.ram_usage_pct = psutil.virtual_memory().percent


class WorldModel:
    """Unified system & workspace state model."""

    def __init__(self) -> None:
        self.hardware = SystemHardwareState()
        self.active_services: Dict[str, str] = {}

    def snapshot(self) -> Dict[str, Any]:
        self.hardware.refresh()
        return {
            "computer": {
                "os": f"{self.hardware.os_name} {self.hardware.os_version}",
                "cpu_cores": self.hardware.cpu_count,
                "ram_total_gb": self.hardware.ram_gb,
                "ram_used_pct": self.hardware.ram_usage_pct,
            },
            "runtime_services": self.active_services,
        }


class AgentManager:
    """Manages transient worker agent lifecycles."""

    def __init__(self, permissions_mgr: Optional[PermissionManager] = None) -> None:
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.permissions_mgr = permissions_mgr

    def register_agent(self, agent_id: str, agent_type: str, instance: Any, role: str) -> None:
        self.agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "instance": instance,
            "role": role,
            "state": "IDLE",
        }
        if self.permissions_mgr:
            self.permissions_mgr.assign_role(agent_id, role)
        logger.info(f"Registered Agent '{agent_id}' ({agent_type}) under role '{role}'")


# ============================================================================
# 6. TAMPER-EVIDENT AUDIT SERVICE
# ============================================================================

@dataclass
class AuditRecord:
    record_id: str = field(
        default_factory=lambda: f"AUD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:17]}"
    )
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: str = "system"
    action: str = "UNKNOWN_ACTION"
    target: str = "N/A"
    permission_status: str = "GRANTED"
    execution_result: str = "SUCCESS"
    previous_hash: str = GENESIS_HASH
    record_hash: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class AuditService:
    """Hash-chained ledger for security tracking."""

    def __init__(self, log_dir: str = "logs/audit") -> None:
        self.log_path = Path(log_dir)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self._current_file = self.log_path / f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        self._last_hash = GENESIS_HASH
        self._lock = threading.RLock()

    def log_action(
        self,
        agent_id: str,
        action: str,
        target: str,
        permission_status: str = "GRANTED",
        execution_result: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        with self._lock:
            record = AuditRecord(
                agent_id=agent_id,
                action=action,
                target=target,
                permission_status=permission_status,
                execution_result=execution_result,
                previous_hash=self._last_hash,
                details=details or {},
            )
            raw = json.dumps(asdict(record), sort_keys=True)
            record.record_hash = hashlib.sha256(raw.encode()).hexdigest()
            self._last_hash = record.record_hash

            with open(self._current_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record)) + "\n")

            return record