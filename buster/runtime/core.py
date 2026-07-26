from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.ui.v9.panels.self_improvement.verification.verification_engine import (
    VerificationEngine,
)

from buster.intelligence.agent_tracker import AgentTracker
from buster.intelligence.runtime_monitor import RuntimeMonitor
from buster.intelligence.runtime_snapshot import RuntimeSnapshot

from buster.core.event_bus import main_event_bus
from buster.experience.evolution_state import EvolutionState
from buster.experience.engine import ExperienceEngine

from .dispatcher import RuntimeDispatcher
from .sdk_bootstrap import build_sdk_runtime
from .state_store import RuntimeStateStore

from buster.autonomy.engine import AutonomyEngine
from buster.autonomy.execution_engine import ExecutionEngine
from buster.autonomy.self_improvement_service import SelfImprovementService
from .self_improvement_runtime import (
    register_self_improvement_runtime,
    self_improvement_runtime_status,
    shutdown_self_improvement_runtime,
)

from buster.agents.python_agent import AgentRequest, PreviewDiff, PythonAgentWorker

# v13 Subsystems
from buster.learning.curiosity_engine import CuriosityEngine, CuriosityScore
from buster.kernel.circadian import HeartbeatDaemon

# Phase 19.1, 19.2, 19.3 & 19.4 Rhythm Subsystems
from buster.rhythm.rhythm import BusterRhythm
from buster.rhythm.rhythm_service import RhythmService
from buster.rhythm.task_gate import TaskGate
from buster.rhythm.dlq.dlq_manager import RhythmDLQManager
from buster.rhythm.dlq.worker import DLQRecoveryWorker
from buster.learning.curiosity_evaluator import CuriosityEvaluator
from buster.learning.curiosity_scheduler import CuriosityScheduler
from buster.learning.curiosity_runner import CuriosityRunner

# Phase 21 Subsystem: Hurdle Engine
from buster.hurdle.engine import HurdleEngine
from buster.hurdle.patch_verifier import VerificationResult

# Automation & Workspace Subsystems
from buster.automation.unified_router import UnifiedAutomationRouter
from buster.workspace.sandbox_manager import SandboxManager

from buster.autonomy.goals.goal_service import GoalService


class BusterRuntimeCore:
    def __init__(
        self,
        root: str | Path = ".",
        observation_provider=None,
    ):
        self.root = Path(root).resolve()

        # --------------------------------------------------
        # 1. Primary SDK & Kernel Runtime Construction
        # --------------------------------------------------
        self.system = build_sdk_runtime(
            root=self.root,
            observation_provider=observation_provider,
        )

        self.runtime = self.system["runtime"]
        self.sdk = self.system["sdk"]
        self.events = self.sdk.events
        self.services = self.sdk.registry

        self.agents = self.system["agents"]
        self.registry = self.system["registry"]
        self.jobs = self.system["jobs"]
        self.workflow = self.system["workflow"]
        self.blackboard = self.system["blackboard"]
        self.agent_memory = self.system["agent_memory"]
        self.orchestrator = self.system["orchestrator"]

        # State management & event dispatching
        self.state = RuntimeStateStore()
        self.dispatcher = RuntimeDispatcher(self.state)

        # --------------------------------------------------
        # 2. Canonical Subsystem Instantiation
        # --------------------------------------------------
        
        # AI Manager & Brain Providers
        from buster.brain.providers.manager import AIProviderManager
        self.ai_manager = AIProviderManager(
            self.root / "data" / "ai_provider_config.json"
        )

        # Runtime Intelligence & Telemetry
        self.runtime_monitor = RuntimeMonitor()
        self.agent_tracker = AgentTracker()

        self.dispatcher.subscribe(
            "*",
            self.runtime_monitor.handle_event,
        )
        self.dispatcher.subscribe(
            "agent.*",
            self.agent_tracker.handle_event,
        )

        self.runtime_snapshot = RuntimeSnapshot(
            self,
            runtime_monitor=self.runtime_monitor,
            agent_tracker=self.agent_tracker,
        )

        # Autonomy & Execution Subsystems
        self.autonomy_engine = AutonomyEngine(
            state_path=self.root / "data" / "autonomy_state.json",
            history_path=self.root / "data" / "autonomy_history.json",
        )

        self.execution_engine = ExecutionEngine(
            root=self.root,
            runtime_core=self,
            autonomy_engine=self.autonomy_engine,
        )

        # Evolution, Memory & Experience
        self.evolution = EvolutionState(
            state_dir=str(self.root / "data"),
            event_bus=main_event_bus,
        )
        self.identity = self.evolution  # Compatibility alias

        self.experience_engine = ExperienceEngine(
            data_dir=str(self.root / "data"),
        )

        # v13: Curiosity Engine & Heartbeat Rhythm
        self.curiosity_engine = CuriosityEngine(
            data_dir=self.root / "data",
        )

        self.heartbeat_daemon = HeartbeatDaemon(
            runtime_core=self,
        )

        # Phase 19.1, 19.2 & 19.4: Rhythm Core Engine, Task Gate, DLQ & Recovery Worker
        self.rhythm = BusterRhythm()
        self.rhythm_service = RhythmService(
            rhythm=self.rhythm,
            blackboard=self.blackboard,
            event_bus=self.dispatcher,
        )
        self.task_gate = TaskGate()
        self.dlq_manager = RhythmDLQManager(
            rhythm=self.rhythm,
            storage_path=self.root / "data" / "dlq_state.json",
            event_bus=self.dispatcher,
        )
        self.dlq_worker = DLQRecoveryWorker(
            dlq_manager=self.dlq_manager,
            execution_engine=self.execution_engine,
        )

        self.verification_service = VerificationEngine(
            project_root=self.root,
        )
        
        # Initialize Intrinsic Curiosity Engine
        self.curiosity_evaluator = CuriosityEvaluator(project_root=self.root)
        self.curiosity_scheduler = CuriosityScheduler(
            evaluator=self.curiosity_evaluator,
            rhythm_service=self.rhythm_service,
        )
        self.curiosity_runner = CuriosityRunner(project_root=self.root)

        # Phase 21: Hurdle Engine
        self.hurdle_engine = HurdleEngine(project_root=self.root)

        # Unified Automation Router & Sandbox Workspace
        self.automation_router = UnifiedAutomationRouter(
            event_bus=self.dispatcher,
            security_intercept=getattr(self, "security", None),
        )

        self.sandbox_manager = SandboxManager(
            root_dir=self.root,
        )

        # Repair & Self-Improvement
        self.self_improvement = SelfImprovementService(
            root=self.root,
            runtime_core=self,
            autonomy_engine=self.autonomy_engine,
            execution_engine=self.execution_engine,
        )
        self.self_improvement.set_mode("manual")

        self.python_agent_worker = PythonAgentWorker(
            provider=self.ai_manager,
            event_bus=self.dispatcher,
            max_retries=3,
            score_threshold=90.0,
        )

        self._repair_workers = {
            "python": self.python_agent_worker,
        }
        # Autonomous Goal Runtime
        self.goal_service = GoalService(runtime_core=self)

        # Subsystem Services & Monitors
        from buster.intelligence.health_monitor import HealthMonitor
        self.health_monitor = HealthMonitor(self)

        from .dev_tools import RuntimeDeveloperTools
        self.devtools = RuntimeDeveloperTools(self)

        from .inspector import RuntimeInspector
        self.inspector = RuntimeInspector(self)

        # --------------------------------------------------
        # 3. Service Registry Consolidation
        # --------------------------------------------------
        self._register_core_services()

        self.self_improvement_service = (
            register_self_improvement_runtime(self)
        )
        self.repair_service = self.self_improvement_service

        self.started = False
        self.refresh_state()

    def _register_core_services(self) -> None:
        """Register all permanent core subsystems in the ServiceRegistry."""
        core_services = {
            "ai": self.ai_manager,
            "python_agent": self.python_agent_worker,
            "autonomy": self.autonomy_engine,
            "goal_service": self.goal_service,
            "execution": self.execution_engine,
            "evolution": self.evolution,
            "experience": self.experience_engine,
            "curiosity": self.curiosity_engine,
            "rhythm": self.rhythm_service,
            "dlq": self.dlq_manager,
            "dlq_worker": self.dlq_worker,
            "verification": self.verification_service,
            "automation_router": self.automation_router,
            "sandbox_manager": self.sandbox_manager,
            "self_improvement": self.self_improvement,
            "health_monitor": self.health_monitor,
            "hurdle_engine": self.hurdle_engine,
        }

        for name, instance in core_services.items():
            try:
                self.services.register(name, instance)
            except Exception:
                pass

    # --------------------------------------------------
    # Hurdle Exception Handler
    # --------------------------------------------------

    def handle_hurdle_exception(
        self,
        exc: Exception,
        replacement_code: str | None = None,
        test_command: list[str] | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> VerificationResult:
        """Processes runtime exceptions through the HurdleEngine and dispatches result events."""
        result = self.hurdle_engine.process_exception(
            exc=exc,
            replacement_code=replacement_code,
            test_command=test_command,
            file_path=file_path,
            line_number=line_number,
        )

        event_name = "hurdle.resolved" if result.applied else "hurdle.failed"
        self.dispatcher.publish(
            event_name,
            {
                "candidate_id": result.candidate_id,
                "target_path": result.target_path,
                "applied": result.applied,
                "tests_passed": result.tests_passed,
                "rollback_performed": result.rollback_performed,
                "issues": result.issues,
            },
            source="runtime_core",
        )

        return result

    # --------------------------------------------------
    # Atomic Runtime Lifecycle Entry Points
    # --------------------------------------------------

    def start(self) -> Dict[str, Any]:
        """Single consolidated entry point for starting the entire AI OS runtime."""
        if self.started:
            return self.runtime.status()

        result = self.runtime.start()
        self.started = True

        # Start background rhythm
        self.heartbeat_daemon.start()

        event = {
            "root": str(self.root),
            "started": True,
        }

        self.events.publish(
            "runtime.core.started",
            event,
            source="runtime_core",
        )

        self.dispatcher.publish(
            "runtime.started",
            event,
            source="runtime_core",
        )

        self.refresh_state()
        return result

    def stop(self) -> Dict[str, Any]:
        """Single consolidated entry point for shutting down all services."""
        if not self.started:
            return self.runtime.status()

        # Stop background rhythm
        self.heartbeat_daemon.stop()

        # Teardown self-improvement background processes
        shutdown_self_improvement_runtime(
            self,
            wait=False,
        )

        result = self.runtime.stop()
        self.started = False

        event = {
            "root": str(self.root),
            "started": False,
        }

        self.events.publish(
            "runtime.core.stopped",
            event,
            source="runtime_core",
        )

        self.dispatcher.publish(
            "runtime.stopped",
            event,
            source="runtime_core",
        )

        self.refresh_state()
        return result

    def tick(
        self,
        observations: list[dict[str, Any]] | None = None,
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        # Handle time-sync for rhythm engine and recovery worker
        self.rhythm_service.tick_sync(now=now)

        # Safely pass observations list to underlying engine
        engine_obs = observations if isinstance(observations, list) else None
        result = self.runtime.tick_once(engine_obs)

        # Process ready DLQ recovery items via worker using the explicit timestamp
        processed_count = self.dlq_worker.process_ready_items(now=now)
        if processed_count > 0:
            self.dispatcher.publish(
                "dlq.recovery_executed",
                {
                    "processed_count": processed_count,
                },
                source="runtime_core",
            )

        # Intrinsic Curiosity Exploration Cycle
        exploration_tasks = self.curiosity_scheduler.schedule_exploration(now=now, limit=1)
        for exp_task in exploration_tasks:
            exp_result = self.curiosity_runner.inspect_target(exp_task)
            self.dispatcher.publish(
                "curiosity.exploration_completed",
                {
                    "task_id": exp_result.task_id,
                    "target_path": exp_result.target_path,
                    "success": exp_result.success,
                    "summary": exp_result.summary,
                    "issues_found": exp_result.issues_found,
                },
                source="runtime_core",
            )

        self.dispatcher.publish(
            "runtime.tick",
            result,
            source="runtime_core",
        )

        self.refresh_state()
        return result

    # --------------------------------------------------
    # Rhythm Enforcement Helper
    # --------------------------------------------------

    def evaluate_task_gate(self, task_metadata: Dict[str, Any]) -> None:
        """Evaluates whether a task is allowed under current rhythm state."""
        rhythm_status = self.rhythm.get_blackboard_status()
        allowed, reason = self.task_gate.evaluate(task_metadata, rhythm_status)
        if not allowed:
            raise PermissionError(f"Task blocked by Rhythm TaskGate: {reason}")

    # --------------------------------------------------
    # Dispatch & Execution Wrappers
    # --------------------------------------------------

    def run_repair(
        self,
        file_path: str | Path,
        instruction: str,
        language: str = "python",
    ) -> PreviewDiff:
        self.heartbeat_daemon.notify_activity()
        path = Path(file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Target repair file does not exist: {file_path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Target repair path is not a file: {file_path}"
            )

        lang_key = str(language or "python").lower().strip()
        worker = self._repair_workers.get(lang_key)

        if worker is None:
            raise ValueError(
                "No repair worker registered for "
                f"language/platform: {language!r}"
            )

        event_prefix = f"{lang_key}_agent"

        self.dispatcher.publish(
            f"{event_prefix}.started",
            {
                "file": str(path),
                "instruction": instruction,
                "language": lang_key,
            },
            source="runtime_core",
        )

        try:
            original_code = path.read_text(encoding="utf-8")

            request = AgentRequest(
                file_path=str(path),
                instruction=instruction,
                original_code=original_code,
            )

            preview_diff = worker.run(request)

            if not preview_diff.success:
                raise RuntimeError(
                    f"Repair agent [{lang_key}] failed: "
                    f"{preview_diff.error_message}"
                )

            quality = getattr(preview_diff, "quality", None)
            score = getattr(quality, "overall_score", None)

            self.dispatcher.publish(
                f"{event_prefix}.finished",
                {
                    "file": str(path),
                    "score": score,
                    "language": lang_key,
                },
                source="runtime_core",
            )

            return preview_diff

        except Exception as exc:
            self.dispatcher.publish(
                f"{event_prefix}.failed",
                {
                    "file": str(path),
                    "error": str(exc),
                    "language": lang_key,
                },
                source="runtime_core",
            )
            raise

    def run_python_repair(
        self,
        file_path: str | Path,
        instruction: str,
    ) -> PreviewDiff:
        return self.run_repair(
            file_path=file_path,
            instruction=instruction,
            language="python",
        )

    def run(self, request: str, task_metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        task_meta = task_metadata or {
            "priority": "normal",
            "execution_class": "foreground",
            "allowed_states": ["WORK", "LEISURE", "SLEEP"],
            "can_override_inhibitor": True,
        }
        self.evaluate_task_gate(task_meta)

        self.heartbeat_daemon.notify_activity()
        event = {"request": request}

        self.events.publish(
            "runtime.core.request.received",
            event,
            source="runtime_core",
        )

        self.dispatcher.publish(
            "runtime.request",
            event,
            source="runtime_core",
        )

        try:
            result = self.orchestrator.run(request)

            self.dispatcher.publish(
                "runtime.request.finished",
                {
                    "request": request,
                    "result": result,
                },
                source="runtime_core",
            )

            self.refresh_state()
            return result

        except Exception as exc:
            self.dispatcher.publish(
                "runtime.request.failed",
                {
                    "request": request,
                    "error": str(exc),
                },
                source="runtime_core",
            )

            self.refresh_state()
            raise

    def run_agent(self, name: str, task=None, task_metadata: Dict[str, Any] | None = None):
        task_meta = task_metadata or {
            "priority": "normal",
            "execution_class": "foreground",
            "allowed_states": ["WORK", "LEISURE"],
        }
        self.evaluate_task_gate(task_meta)

        self.heartbeat_daemon.notify_activity()
        self.dispatcher.publish(
            "agent.started",
            {
                "agent": name,
                "task": task,
            },
            source="runtime_core",
        )

        try:
            result = self.agents.run(name, task)

            self.dispatcher.publish(
                "agent.finished",
                {
                    "agent": name,
                    "task": task,
                    "result": result,
                },
                source="runtime_core",
            )

            self.refresh_state()
            return result

        except Exception as exc:
            self.dispatcher.publish(
                "agent.failed",
                {
                    "agent": name,
                    "task": task,
                    "error": str(exc),
                },
                source="runtime_core",
            )

            self.refresh_state()
            raise

    def create_job(self, title, job_type="generic", payload=None):
        job = self.jobs.create_job(
            title=title,
            job_type=job_type,
            payload=payload or {},
        )

        self.dispatcher.publish(
            "job.created",
            job,
            source="runtime_core",
        )

        self.refresh_state()
        return job

    def run_job(self, job_id):
        self.heartbeat_daemon.notify_activity()
        self.dispatcher.publish(
            "job.started",
            {"job_id": job_id},
            source="runtime_core",
        )

        try:
            result = self.jobs.run_job(job_id)

            self.dispatcher.publish(
                "job.finished",
                {
                    "job_id": job_id,
                    "result": result,
                },
                source="runtime_core",
            )

            self.refresh_state()
            return result

        except Exception as exc:
            self.dispatcher.publish(
                "job.failed",
                {
                    "job_id": job_id,
                    "error": str(exc),
                },
                source="runtime_core",
            )

            self.refresh_state()
            raise

    # --------------------------------------------------
    # Service Registry & Telemetry Proxies
    # --------------------------------------------------

    def service(self, name: str, default=None):
        return self.sdk.service(name, default)

    def require_service(self, name: str):
        return self.sdk.require_service(name)

    def status(self) -> Dict[str, Any]:
        registry_status = self.registry.status()
        job_status = self.jobs.status()
        memory_status = self.agent_memory.status()

        return {
            "root": str(self.root),
            "started": self.started,
            "runtime": self.runtime.status(),
            "sdk": self.sdk.status(),
            "registry_summary": registry_status.get("summary", {}),
            "jobs": job_status,
            "agents": self.agents.status(),
            "blackboard": self.blackboard.snapshot(),
            "agent_memory": memory_status,
            "recent_events": self.events.recent(20),
            "state": self.state.snapshot(),
            "dispatcher": self.dispatcher.status(),
            "ai": self._ai_status(),
            "autonomy": self.autonomy_engine.status(),
            "execution": self.execution_engine.status(),
            "curiosity": self.curiosity_engine.status(),
            "circadian": self.heartbeat_daemon.status(),
            "rhythm": self.rhythm.get_blackboard_status(),
            "dlq": self.dlq_manager.status(),
            "automation_router": self.automation_router.status(),
            "sandbox_manager": self.sandbox_manager.status(),
            "self_improvement": self.self_improvement.status(),
            "repair_workflow": self_improvement_runtime_status(self),
        }

    def _ai_status(self) -> Dict[str, Any]:
        manager = self.ai_manager
        provider_key = str(getattr(manager, "current", "unknown")).lower()

        provider = getattr(manager, "providers", {}).get(provider_key)
        model = getattr(provider, "model", "Unknown")

        if provider is None:
            state = "Unavailable"
            connected = False
        elif provider_key == "local":
            state = "Ready"
            connected = True
        else:
            state = "Configured"
            connected = None

        return {
            "provider": provider_key,
            "model": str(model or "Unknown"),
            "connected": connected,
            "status": state,
            "quick_status": manager.quick_status(),
        }

    def capture_snapshot(
        self,
        event_limit: int = 50,
        activity_limit: int = 50,
    ) -> Dict[str, Any]:
        return self.runtime_snapshot.capture(
            event_limit=event_limit,
            activity_limit=activity_limit,
        )

    def notify(self, title, message, level="info"):
        return self.dispatcher.publish(
            "notification",
            {
                "title": title,
                "message": message,
                "level": level,
            },
            source="runtime_core",
        )

    def refresh_state(self) -> Dict[str, Any]:
        snapshot = {
            "runtime": {
                "started": self.started,
                "status": "running" if self.started else "ready",
                "root": str(self.root),
                "details": self.runtime.status(),
            },
            "jobs": self.jobs.status(),
            "agents": self.agents.status(),
            "memory": self.agent_memory.status(),
            "blackboard": self.blackboard.snapshot(),
            "registry": self.registry.status(),
            "services": self.sdk.status(),
            "ai": self._ai_status(),
            "autonomy": self.autonomy_engine.status(),
            "execution": self.execution_engine.status(),
            "curiosity": self.curiosity_engine.status(),
            "circadian": self.heartbeat_daemon.status(),
            "rhythm": self.rhythm.get_blackboard_status(),
            "dlq": self.dlq_manager.status(),
            "automation_router": self.automation_router.status(),
            "sandbox_manager": self.sandbox_manager.status(),
            "self_improvement": self.self_improvement.status(),
            "repair_workflow": self_improvement_runtime_status(self),
        }

        for key, value in snapshot.items():
            self.state.set(key, value)

        return self.state.snapshot()

    def run_self_improvement(self, mode="manual"):
        self.heartbeat_daemon.notify_activity()
        result = self.self_improvement.run_cycle(mode=mode)
        data = result.to_dict()

        self.dispatcher.publish(
            "self_improvement.finished",
            data,
            source="runtime_core",
        )

        self.refresh_state()
        return result

    def self_improvement_status(self):
        return self.self_improvement.status()

    def autonomy_status(self):
        return self.autonomy_engine.status()

    def execution_status(self):
        return self.execution_engine.status()

    def health(self):
        return self.health_monitor.compact()

    def repair_workflow_status(self):
        return self.improvement_runtime_status(self)

    def recover_repair_sessions(self):
        return self.self_improvement_service.recover_sessions()

    def active_repair_sessions(self):
        return self.self_improvement_service.active_sessions()

    def record_evolution_action(
        self,
        action: str,
        *,
        success: bool,
    ) -> None:
        experience_engine = getattr(self, "experience_engine", None)
        evolution = getattr(self, "evolution", None)

        if experience_engine is None or evolution is None:
            return

        experience_engine.process_evolution_xp(
            evolution,
            main_event_bus,
            action,
            success=success,
        )


def create_runtime_core(
    root: str | Path = ".",
    observation_provider=None,
) -> BusterRuntimeCore:
    return BusterRuntimeCore(
        root=root,
        observation_provider=observation_provider,
    )