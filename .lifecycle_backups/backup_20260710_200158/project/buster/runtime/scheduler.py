from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from .storage import now
class RuntimeScheduler:
    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
    def add_job(self, name: str, interval_ticks: int, task: Optional[Callable[[], Any]] = None, enabled: bool = True) -> Dict[str, Any]:
        job = {'name': name, 'interval_ticks': max(1, int(interval_ticks)), 'last_tick': 0, 'enabled': enabled, 'created_at': now(), '_task': task}
        self.jobs.append(job)
        return {k:v for k,v in job.items() if k != '_task'}
    def due_jobs(self, tick: int) -> List[Dict[str, Any]]:
        return [job for job in self.jobs if job.get('enabled') and tick - int(job.get('last_tick', 0)) >= int(job.get('interval_ticks', 1))]
    def run_due(self, tick: int) -> List[Dict[str, Any]]:
        results=[]
        for job in self.due_jobs(tick):
            result=None; ok=True
            try:
                if job.get('_task'): result = job['_task']()
            except Exception as exc:
                ok=False; result=str(exc)
            job['last_tick'] = tick
            results.append({'name': job['name'], 'ok': ok, 'result': result, 'ran_at': now()})
        return results
