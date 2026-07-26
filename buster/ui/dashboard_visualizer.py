# buster/ui/dashboard_visualizer.py
from __future__ import annotations

import html
import json
from buster.mission_control.snapshot import MissionControlSnapshot


class DashboardVisualizer:
    """Converts MissionControlSnapshot instances into formatted ANSI terminal or HTML representations."""

    def render_ansi(self, snapshot: MissionControlSnapshot) -> str:
        health_color = (
            "\033[92m" if snapshot.health == "HEALTHY"
            else "\033[93m" if snapshot.health == "DEGRADED"
            else "\033[91m"
        )
        reset = "\033[0m"

        lines = [
            "==========================================================================",
            " 🚀 BUSTER MISSION CONTROL PANEL",
            "==========================================================================",
            f" System Health : {health_color}{snapshot.health}{reset} | Generated: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f" Active Tasks  : {snapshot.active_tasks} | Completed: {snapshot.completed_tasks} | Failed: {snapshot.failed_tasks} | DLQ: {snapshot.dlq_count}",
            "--------------------------------------------------------------------------",
            " 🐝 ACTIVE WORKER LEASES:",
        ]

        if snapshot.active_leases:
            for lease in snapshot.active_leases:
                lines.append(
                    f"   • [{lease.role}] {lease.worker_id} -> Task: {lease.task_id} ({lease.remaining_seconds:.1f}s remaining)"
                )
        else:
            lines.append("   (No active worker leases)")

        lines.append("--------------------------------------------------------------------------")
        lines.append(" ⚡ CIRCUIT BREAKERS:")
        if snapshot.circuits:
            for cb in snapshot.circuits:
                state_str = (
                    f"\033[92m{cb.state}{reset}" if cb.state == "CLOSED"
                    else f"\033[91m{cb.state}{reset}"
                )
                lines.append(f"   • {cb.circuit_id:<20}: {state_str} (Failures: {cb.failure_count})")
        else:
            lines.append("   (No circuit breakers registered)")

        lines.append("==========================================================================")
        return "\n".join(lines)

    def render_html(self, snapshot: MissionControlSnapshot) -> str:
        health_class = snapshot.health.lower()
        
        leases_html = "".join(
            f"<li>⚡ <strong>{html.escape(l.worker_id)}</strong> ({html.escape(l.role)}) &mdash; Task: <code>{html.escape(l.task_id)}</code> [{l.remaining_seconds:.1f}s]</li>"
            for l in snapshot.active_leases
        ) or "<li>No active leases.</li>"

        circuits_html = "".join(
            f"<li>⚙️ <strong>{html.escape(c.circuit_id)}</strong>: <span class=\"state-{html.escape(c.state.lower())}\">{html.escape(c.state)}</span> (Failures: {c.failure_count})</li>"
            for c in snapshot.circuits
        ) or "<li>No active circuits.</li>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Buster Mission Control</title>
    <style>
        body {{ background: #0f172a; color: #f8fafc; font-family: monospace; padding: 20px; }}
        .healthy {{ color: #4ade80; }} .degraded {{ color: #facc15; }} .critical {{ color: #f87171; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <h1>🚀 Mission Control & System Health</h1>
    <p>Overall Health: <span class="{health_class}"><strong>{html.escape(snapshot.health)}</strong></span></p>
    <div class="grid">
        <div class="card">
            <h3>🐝 Active Worker Leases ({snapshot.active_tasks})</h3>
            <ul>{leases_html}</ul>
        </div>
        <div class="card">
            <h3>⚡ Circuit Breakers</h3>
            <ul>{circuits_html}</ul>
        </div>
    </div>
</body>
</html>"""

    def export_json(self, snapshot: MissionControlSnapshot) -> str:
        return json.dumps(
            {
                "generated_at": snapshot.generated_at.isoformat(),
                "health": snapshot.health,
                "active_tasks": snapshot.active_tasks,
                "completed_tasks": snapshot.completed_tasks,
                "failed_tasks": snapshot.failed_tasks,
                "dlq_count": snapshot.dlq_count,
                "active_leases": [
                    {
                        "lease_id": l.lease_id,
                        "worker_id": l.worker_id,
                        "role": l.role,
                        "task_id": l.task_id,
                        "remaining_seconds": l.remaining_seconds,
                    }
                    for l in snapshot.active_leases
                ],
                "circuits": [
                    {
                        "circuit_id": c.circuit_id,
                        "state": c.state,
                        "failure_count": c.failure_count,
                    }
                    for c in snapshot.circuits
                ],
                "metrics": snapshot.metrics,
            },
            indent=2,
        )