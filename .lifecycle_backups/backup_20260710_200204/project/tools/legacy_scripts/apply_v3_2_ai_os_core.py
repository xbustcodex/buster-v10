from pathlib import Path

ROOT = Path(__file__).parent
BUSTER = ROOT / "buster"

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote", path)

write(BUSTER / "services" / "job_queue.py", r'''
from __future__ import annotations

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


@dataclass
class Job:
    id: str
    title: str
    status: str = "queued"
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class JobQueue:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, title: str, fn: Callable[[], Any]) -> Job:
        job = Job(id=str(uuid.uuid4())[:8], title=title)

        with self._lock:
            self.jobs[job.id] = job

        thread = threading.Thread(
            target=self._run,
            args=(job.id, fn),
            daemon=True,
        )
        thread.start()
        return job

    def _run(self, job_id: str, fn: Callable[[], Any]):
        job = self.jobs[job_id]
        job.status = "running"
        job.started_at = time.time()

        try:
            job.result = fn()
            job.status = "finished"
        except Exception as e:
            job.error = str(e)
            job.status = "failed"
        finally:
            job.finished_at = time.time()

    def list_jobs(self):
        with self._lock:
            return list(self.jobs.values())

    def get(self, job_id: str):
        return self.jobs.get(job_id)
''')

write(BUSTER / "repository" / "project_model.py", r'''
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectModel:
    root: str
    files: int = 0
    python_files: int = 0
    classes: int = 0
    functions: int = 0
    imports: int = 0
    todos: int = 0
    errors: int = 0


class ProjectAnalyzer:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def analyze(self) -> ProjectModel:
        model = ProjectModel(root=str(self.root))

        for path in self.root.rglob("*"):
            if "__pycache__" in path.parts:
                continue

            if path.is_file():
                model.files += 1

            if path.suffix == ".py":
                model.python_files += 1
                self._scan_python(path, model)

        return model

    def _scan_python(self, path: Path, model: ProjectModel):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            model.todos += text.lower().count("todo")
            tree = ast.parse(text)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    model.classes += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    model.functions += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    model.imports += 1

        except Exception:
            model.errors += 1
''')

write(BUSTER / "workspace" / "ai_os.py", r'''
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
''')

write(BUSTER / "workspace" / "__init__.py", r'''
from .ai_os import AIOSCore

__all__ = ["AIOSCore"]
''')

write(ROOT / "test_v3_2_ai_os_core.py", r'''
from pathlib import Path

from buster.workspace.ai_os import AIOSCore
from buster.repository.project_model import ProjectAnalyzer


def main():
    root = Path(__file__).parent

    print("=== Buster v3.2 AI OS Core Test ===")

    analyzer = ProjectAnalyzer(root)
    model = analyzer.analyze()

    print("Project Model")
    print("Files:", model.files)
    print("Python files:", model.python_files)
    print("Classes:", model.classes)
    print("Functions:", model.functions)
    print("Imports:", model.imports)
    print("TODOs:", model.todos)
    print("Errors:", model.errors)

    ai_os = AIOSCore(root)
    job = ai_os.rebuild_project_model()

    print()
    print("Started background job:", job.id, job.title)

    import time
    for _ in range(20):
        status = ai_os.status()
        job_status = status["jobs"][0]["status"]
        print("Job status:", job_status)
        if job_status in ("finished", "failed"):
            break
        time.sleep(0.2)

    print()
    print("AI OS Status:")
    print(ai_os.status())

    print()
    print("SUCCESS: v3.2 AI OS Core installed.")


if __name__ == "__main__":
    main()
''')

print()
print("Buster v3.2 AI OS Core patch complete.")
print("Run:")
print("python test_v3_2_ai_os_core.py")
''