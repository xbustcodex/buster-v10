from __future__ import annotations

from pathlib import Path

from buster.services.job_queue import JobQueue
from buster.repository.project_model import ProjectAnalyzer


class AIOSCore:
    """
    Central coordinator for Buster's desktop AI operating environment.
    This connects background jobs, repository understanding, and agent teams.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.jobs = JobQueue()
        self.last_project_model = None

    def rebuild_project_model(self):
        def task():
            analyzer = ProjectAnalyzer(self.project_root)
            self.last_project_model = analyzer.analyze()
            return self.last_project_model

        return self.jobs.submit("Rebuild project model", task)

    def run_agent_team_job(self, request: str):
        def task():
            try:
                from buster.agents.team import AgentTeam
                team = AgentTeam()
                if hasattr(team, "run"):
                    return team.run(request)
                if hasattr(team, "execute"):
                    return team.execute(request)
                return "AgentTeam loaded, but no run/execute method was found."
            except Exception as e:
                return f"Agent team job failed: {e}"

        return self.jobs.submit(f"Agent Team: {request[:40]}", task)

    def status(self):
        model = self.last_project_model
        jobs = self.jobs.list_jobs()

        return {
            "project_root": str(self.project_root),
            "files": getattr(model, "files", 0) if model else 0,
            "python_files": getattr(model, "python_files", 0) if model else 0,
            "classes": getattr(model, "classes", 0) if model else 0,
            "functions": getattr(model, "functions", 0) if model else 0,
            "imports": getattr(model, "imports", 0) if model else 0,
            "todos": getattr(model, "todos", 0) if model else 0,
            "errors": getattr(model, "errors", 0) if model else 0,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "status": job.status,
                    "error": job.error,
                }
                for job in jobs
            ],
        }
