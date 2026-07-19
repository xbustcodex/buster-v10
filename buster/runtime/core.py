from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.intelligence.agent_tracker import AgentTracker
from buster.intelligence.runtime_monitor import RuntimeMonitor
from buster.intelligence.runtime_snapshot import RuntimeSnapshot

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


  
class BusterRuntimeCore:
    def __init__(
        self,
        root: str | Path = ".",
        observation_provider=None,
    ):
        self.root = Path(root).resolve()

        self.system = build_sdk_runtime(
            root=self.root,
            observation_provider=observation_provider,
        )

        # Core SDK runtime components
        self.runtime = self.system["runtime"]
        self.sdk = self.system["sdk"]
        self.events = self.sdk.events
        self.services = self.sdk.registry

        # Runtime systems
        self.agents = self.system["agents"]
        self.registry = self.system["registry"]
        self.jobs = self.system["jobs"]
        self.workflow = self.system["workflow"]
        self.blackboard = self.system["blackboard"]
        self.agent_memory = self.system["agent_memory"]
        self.orchestrator = self.system["orchestrator"]
        
        # --------------------------------------------------
        # Shared AI Provider Manager
        # --------------------------------------------------

        from buster.brain.providers.manager import AIProviderManager

        self.ai_manager = AIProviderManager(
            self.root / "data" / "ai_provider_config.json"
        )

        # Register as a runtime service so every panel can use it
        try:
            self.services.register("ai", self.ai_manager)
        except Exception:
            pass
            

        # Shared runtime state and dispatcher must be created before
        # Runtime Intelligence subscribes to events.
        self.state = RuntimeStateStore()
        self.dispatcher = RuntimeDispatcher(self.state)

        # Runtime Intelligence
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
        
        self.autonomy_engine = AutonomyEngine(
            state_path=self.root / "data" / "autonomy_state.json",
            history_path=self.root / "data" / "autonomy_history.json",
        )

        self.execution_engine = ExecutionEngine(
            root=self.root,
            runtime_core=self,
            autonomy_engine=self.autonomy_engine,
        )

        self.self_improvement = SelfImprovementService(
            root=self.root,
            runtime_core=self,
            autonomy_engine=self.autonomy_engine,
            execution_engine=self.execution_engine,
        )
        
        self.self_improvement.set_mode("manual")
        
        # Runtime-owned repair workflow service.
        # self.self_improvement remains the project scan service.
        # self.self_improvement_service owns repair sessions.

        self.self_improvement_service = (
            register_self_improvement_runtime(self)
        )

        # Compatibility alias
        self.repair_service = self.self_improvement_service
        
        from buster.intelligence.health_monitor import HealthMonitor

        self.health_monitor = HealthMonitor(self)

        # Developer tools
        from .dev_tools import RuntimeDeveloperTools

        self.devtools = RuntimeDeveloperTools(self)

        # Runtime inspector
        from .inspector import RuntimeInspector

        self.inspector = RuntimeInspector(self)

        self.started = False

        # Build the initial shared state.
        self.refresh_state()

    def start(self) -> Dict[str, Any]:
        result = self.runtime.start()
        self.started = True

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

    def tick(self, observations=None) -> Dict[str, Any]:
        result = self.runtime.tick_once(observations)

        self.dispatcher.publish(
            "runtime.tick",
            result,
            source="runtime_core",
        )

        self.refresh_state()
        return result

    def run(self, request: str) -> Dict[str, Any]:
        event = {
            "request": request,
        }

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

    def run_agent(
        self,
        name: str,
        task=None,
    ):
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

    def create_job(
        self,
        title,
        job_type="generic",
        payload=None,
    ):
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
        self.dispatcher.publish(
            "job.started",
            {
                "job_id": job_id,
            },
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

    def service(
        self,
        name: str,
        default=None,
    ):
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
            "registry_summary": registry_status.get(
                "summary",
                {},
            ),
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

            "self_improvement": self.self_improvement.status(),
            
            "repair_workflow": self_improvement_runtime_status(self),
        }

    def _ai_status(self) -> Dict[str, Any]:
        """
        Return AI configuration without performing network requests.

        Provider availability checks must never run from status(), refresh_state(),
        sidebar refreshes, timers, or the Qt UI thread. Use the Settings panel's
        explicit Test Connection action for live diagnostics.
        """
        manager = self.ai_manager
        provider_key = str(
            getattr(manager, "current", "unknown")
        ).lower()

        provider = getattr(
            manager,
            "providers",
            {},
        ).get(provider_key)

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

    def notify(
        self,
        title,
        message,
        level="info",
    ):
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
                "status": (
                    "running"
                    if self.started
                    else "ready"
                ),
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

            "self_improvement": self.self_improvement.status(),
            
            "repair_workflow": self_improvement_runtime_status(self),
        }

        for key, value in snapshot.items():
            self.state.set(key, value)

        return self.state.snapshot()
        
        
    def run_self_improvement(
        self,
        mode="manual",
    ):
        result = self.self_improvement.run_cycle(
            mode=mode,
        )

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
        return self_improvement_runtime_status(self)


    def recover_repair_sessions(self):
        return self.self_improvement_service.recover_sessions()


    def active_repair_sessions(self):
        return self.self_improvement_service.active_sessions()        


def create_runtime_core(
    root: str | Path = ".",
    observation_provider=None,
) -> BusterRuntimeCore:
    return BusterRuntimeCore(
        root=root,
        observation_provider=observation_provider,
    )