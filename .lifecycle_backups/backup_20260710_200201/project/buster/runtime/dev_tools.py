from __future__ import annotations

from typing import Any, Dict

from .inspector import RuntimeInspector
from .plugin_inspector import PluginInspector
from .workflow_graph import WorkflowGraphBuilder


class RuntimeDeveloperTools:
    def __init__(self, core):
        self.core = core
        self.inspector = RuntimeInspector(core)
        self.workflow_graph = WorkflowGraphBuilder(core)
        self.plugins = PluginInspector(core)

    def dashboard_payload(self) -> Dict[str, Any]:
        return {
            "runtime": self.inspector.runtime_summary(),
            "services": self.inspector.services(),
            "agents": self.inspector.agents(),
            "jobs": self.inspector.jobs(),
            "workflow_graph": self.workflow_graph.from_jobs(),
            "event_graph": self.workflow_graph.from_recent_events(25),
            "plugins": self.plugins.status(),
            "events": self.inspector.events(25),
        }
