from __future__ import annotations

from typing import Any, Dict, List


class RuntimeInspector:
    def __init__(self, core):
        self.core = core

    def runtime_summary(self) -> Dict[str, Any]:
        status = self.core.status()
        return {
            "started": status.get("started"),
            "root": status.get("root"),
            "registry": status.get("registry_summary"),
            "job_count": status.get("jobs", {}).get("count", 0),
            "event_count": len(self.core.events.history),
            "agents": self.core.agents.names(),
            "services": self.core.sdk.registry.names(),
        }

    def services(self) -> Dict[str, Any]:
        return self.core.registry.status().get("services", {})

    def agents(self) -> Dict[str, Any]:
        return self.core.registry.status().get("agents", {})

    def jobs(self) -> Dict[str, Any]:
        return self.core.jobs.status()

    def events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.core.events.recent(limit)

    def blackboard(self) -> Dict[str, Any]:
        return self.core.blackboard.snapshot()

    def agent_memory(self) -> Dict[str, Any]:
        return self.core.agent_memory.status()

    def capabilities(self) -> Dict[str, Any]:
        return self.core.registry.status().get("capabilities", {})

    def full_report(self) -> Dict[str, Any]:
        return self.snapshot()


    def dispatcher(self) -> Dict[str, Any]:
        return self.core.dispatcher.status()


    def state_store(self) -> Dict[str, Any]:
        return self.core.state.status()


    def workflow(self) -> Dict[str, Any]:
        workflow = getattr(self.core, "workflow", None)

        if workflow is None:
            return {
                "available": False,
                "status": "unavailable",
            }

        status_method = getattr(workflow, "status", None)

        if callable(status_method):
            return status_method()

        result = {
            "available": True,
            "type": type(workflow).__name__,
        }

        for attribute in (
            "current_workflow",
            "current_step",
            "running",
            "last_result",
            "history",
            "steps",
        ):
            if hasattr(workflow, attribute):
                try:
                    result[attribute] = getattr(workflow, attribute)
                except Exception as exc:
                    result[attribute] = f"Unavailable: {exc}"

        if len(result) == 2:
            result["status"] = "ready"

        return result


    def orchestrator(self) -> Dict[str, Any]:
        orchestrator = getattr(self.core, "orchestrator", None)

        if orchestrator is None:
            return {
                "available": False,
                "status": "unavailable",
            }

        status_method = getattr(orchestrator, "status", None)

        if callable(status_method):
            return status_method()

        return {
            "available": True,
            "type": type(orchestrator).__name__,
            "status": "ready",
        }
        
        
    def _service_status(self, service_name: str) -> Dict[str, Any]:
        service = self.core.service(service_name)

        if service is None:
            return {
                "available": False,
                "status": "unavailable",
            }

        status_method = getattr(service, "status", None)

        if callable(status_method):
            return status_method()

        result = {
            "available": True,
            "type": type(service).__name__,
            "status": "ready",
        }

        for attr in (
            "running",
            "enabled",
            "jobs",
            "queue",
            "tasks",
            "last_run",
            "interval",
        ):
            if hasattr(service, attr):
                try:
                    result[attr] = getattr(service, attr)
                except Exception:
                    pass

        return result    


    def registry(self) -> Dict[str, Any]:
        return self.core.registry.status()


    def sdk(self) -> Dict[str, Any]:
        return self.core.sdk.status()


    def runtime(self) -> Dict[str, Any]:
        return self.core.runtime.status()


    def scheduler(self) -> Dict[str, Any]:
        return self._service_status("scheduler")


    def heartbeat(self) -> Dict[str, Any]:
        return self._service_status("heartbeat")


    def watchdog(self) -> Dict[str, Any]:
        return self._service_status("watchdog")


    def coordinator(self) -> Dict[str, Any]:
        return self._service_status("coordinator")


    def predictor(self) -> Dict[str, Any]:
        return self._service_status("intent_prediction")
        
        
    def diagnostics(self) -> Dict[str, Any]:
        return {
            "runtime": self.runtime(),
            "dispatcher": self.dispatcher(),
            "state_store": self.state_store(),
            "registry": self.registry(),
            "workflow": self.workflow(),
            "orchestrator": self.orchestrator(),
            "scheduler": self.scheduler(),
            "heartbeat": self.heartbeat(),
            "watchdog": self.watchdog(),
            "coordinator": self.coordinator(),
            "predictor": self.predictor(),
        }    
        
        
        
    def health(self) -> Dict[str, Any]:
        return {
            "runtime": "healthy",
            "dispatcher": "healthy",
            "registry": "healthy",
            "workflow": "healthy",
            "jobs": "healthy",
            "memory": "healthy",
            "blackboard": "healthy",
        } 


    def statistics(self) -> Dict[str, Any]:
        return {
            "events": len(self.events(100000)),
            "agents": len(self.core.agents.names()),
            "services": len(self.core.sdk.registry.names()),
            "jobs": self.jobs().get("count", 0),
            "capabilities": len(self.capabilities()),
        }   


    def snapshot(self) -> Dict[str, Any]:
        return {
            "summary": self.runtime_summary(),
            "statistics": self.statistics(),
            "diagnostics": self.diagnostics(),
            "health": self.health(),
            "events": self.events(50),
            "jobs": self.jobs(),
            "agents": self.agents(),
            "services": self.services(),
            "blackboard": self.blackboard(),
            "agent_memory": self.agent_memory(),
        }  


        