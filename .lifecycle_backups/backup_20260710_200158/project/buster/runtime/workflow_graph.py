from __future__ import annotations

from typing import Any, Dict, List


class WorkflowGraphBuilder:
    def __init__(self, core):
        self.core = core

    def from_jobs(self) -> Dict[str, Any]:
        jobs = self.core.jobs.list_jobs()

        nodes = []
        edges = []

        previous_id = None

        for job in jobs:
            job_id = job.get("job_id")
            node = {
                "id": job_id,
                "label": job.get("title"),
                "type": job.get("type"),
                "status": job.get("status"),
            }
            nodes.append(node)

            if previous_id:
                edges.append({
                    "from": previous_id,
                    "to": job_id,
                    "type": "sequence",
                })

            previous_id = job_id

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
        }

    def from_recent_events(self, limit: int = 40) -> Dict[str, Any]:
        events = self.core.events.recent(limit)

        nodes = []
        edges = []

        last_agent_event = None

        for index, event in enumerate(events):
            event_id = event.get("id") or f"event_{index}"
            nodes.append({
                "id": event_id,
                "label": event.get("type"),
                "source": event.get("source"),
                "priority": event.get("priority"),
            })

            if last_agent_event:
                edges.append({
                    "from": last_agent_event,
                    "to": event_id,
                    "type": "event_flow",
                })

            last_agent_event = event_id

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
        }
