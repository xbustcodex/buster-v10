from __future__ import annotations

import json
import subprocess
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from buster.autonomy.records import AutonomyJob
from buster.intelligence.risk_analysis import RiskAnalyzer, RiskReport
from buster.intelligence.strategy_selector import Strategy, StrategySelector
from buster.utils.datetime_utils import utc_timestamp


def utc_now() -> str:
    return utc_timestamp()


@dataclass
class StepResult:
    step: str
    success: bool
    status: str
    agent: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionResult:
    job_id: str
    success: bool
    status: str
    strategy: str
    risk: Dict[str, Any]
    steps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutionEngine:
    """Execute autonomy jobs through Buster's existing runtime and agents."""

    AGENT_BY_STEP = {
        "inspect": "reviewer",
        "inspect_project": "reviewer",
        "inspect_sketch": "reviewer",
        "plan": "builder",
        "build": "builder",
        "compile": "tester",
        "test": "tester",
        "run_gui": "tester",
        "behavioral_test": "tester",
        "fix_if_needed": "fixer",
        "review": "reviewer",
        "verify": "verifier",
        "learn": "reviewer",
    }

    WRITE_STEPS = {"build", "fix_if_needed", "edit", "refactor", "apply_changes"}

    def __init__(
        self,
        root: str | Path = ".",
        *,
        runtime_core: Any = None,
        autonomy_engine: Any = None,
        risk_analyzer: Optional[RiskAnalyzer] = None,
        strategy_selector: Optional[StrategySelector] = None,
        approval_callback: Optional[Callable[[AutonomyJob, Strategy, RiskReport], bool]] = None,
        step_handlers: Optional[Mapping[str, Callable[[Dict[str, Any]], Any]]] = None,
        history_path: str | Path = "data/execution_history.json",
        max_fix_attempts: int = 2,
    ) -> None:
        self.root = Path(root).resolve()
        self.runtime_core = runtime_core
        self.autonomy_engine = autonomy_engine
        self.risk_analyzer = risk_analyzer or RiskAnalyzer()
        self.strategy_selector = strategy_selector or StrategySelector()
        self.approval_callback = approval_callback
        self.step_handlers = dict(step_handlers or {})
        self.max_fix_attempts = max(0, int(max_fix_attempts))
        self.history_path = self._resolve(history_path)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")

    def preview(
        self,
        request: str,
        *,
        project: str = "default",
        project_type: str = "general",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = dict(context or {})
        strategy = self.strategy_selector.select(
            request,
            {**context, "project": project, "project_type": project_type},
        )
        risk = self.risk_analyzer.analyze(
            request,
            {**context, "project_type": project_type, "missing_tests": not self._has_tests()},
        )
        return {
            "request": request,
            "strategy": strategy.to_dict(),
            "risk": risk.to_dict(),
            "requires_write": any(step in self.WRITE_STEPS for step in strategy.steps),
        }

    def execute(
        self,
        job: AutonomyJob | Mapping[str, Any],
        *,
        strategy: Optional[Strategy] = None,
        context: Optional[Dict[str, Any]] = None,
        mode: str = "assisted",
    ) -> ExecutionResult:
        job_obj = job if isinstance(job, AutonomyJob) else AutonomyJob.from_dict(dict(job))
        context = dict(context or {})
        strategy = strategy or self.strategy_selector.select(
            job_obj.request,
            {**context, "project": job_obj.project, "project_type": job_obj.project_type},
        )
        risk = self.risk_analyzer.analyze(
            job_obj.request,
            {**context, "project_type": job_obj.project_type, "missing_tests": not self._has_tests()},
        )
        result = ExecutionResult(
            job_id=job_obj.job_id,
            success=False,
            status="planning",
            strategy=strategy.name,
            risk=risk.to_dict(),
        )

        allowed, reason = self._allowed(job_obj, strategy, risk, mode)
        if not allowed:
            result.status = "awaiting_approval" if reason == "approval_required" else "blocked"
            result.errors.append(reason)
            return self._finish(result)

        try:
            result.status = "running"
            for step in strategy.steps:
                step_result = self._run_step(step, job_obj, strategy, context)
                result.steps.append(step_result.to_dict())

                if step_result.success:
                    continue

                if step in {"test", "compile", "behavioral_test", "verify"}:
                    if self._fix_loop(job_obj, strategy, context, result):
                        continue

                result.status = "failed"
                result.errors.append(step_result.message or f"Step failed: {step}")
                self._complete_job(job_obj, False, result)
                return self._finish(result)

            result.success = True
            result.status = "completed"
            self._complete_job(job_obj, True, result)
            return self._finish(result)

        except Exception as exc:
            result.status = "failed"
            result.errors.extend([str(exc), traceback.format_exc()])
            self._complete_job(job_obj, False, result)
            return self._finish(result)

    def register_step_handler(self, step: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        if not step or not callable(handler):
            raise ValueError("step and callable handler are required")
        self.step_handlers[step] = handler

    def status(self) -> Dict[str, Any]:
        history = self._history()
        return {
            "root": str(self.root),
            "history_records": len(history),
            "completed": sum(1 for item in history if item.get("status") == "completed"),
            "failed": sum(1 for item in history if item.get("status") == "failed"),
            "registered_handlers": sorted(self.step_handlers),
            "max_fix_attempts": self.max_fix_attempts,
        }

    def _allowed(self, job: AutonomyJob, strategy: Strategy, risk: RiskReport, mode: str) -> tuple[bool, str]:
        if mode not in {"manual", "assisted", "autonomous"}:
            return False, f"invalid_mode:{mode}"
        if risk.level == "blocked":
            return False, "blocked:" + ",".join(risk.blockers)
        if mode == "manual":
            return False, "approval_required"
        requires_write = any(step in self.WRITE_STEPS for step in strategy.steps)
        if mode == "assisted" or risk.level in {"medium", "high"}:
            if not requires_write and risk.level == "low":
                return True, "read_only"
            if self.approval_callback is None:
                return False, "approval_required"
            return (True, "approved") if self.approval_callback(job, strategy, risk) else (False, "approval_required")
        return True, "autonomous_low_risk"

    def _run_step(
        self,
        step: str,
        job: AutonomyJob,
        strategy: Strategy,
        context: Dict[str, Any],
    ) -> StepResult:
        started = utc_now()
        agent = self.AGENT_BY_STEP.get(step, "")
        payload = {
            "step": step,
            "job": job.to_dict(),
            "strategy": strategy.to_dict(),
            "context": context,
            "root": str(self.root),
            "agent": agent,
        }
        try:
            if step in self.step_handlers:
                raw = self.step_handlers[step](payload)
            elif step == "compile":
                raw = self._run_command(["python", "-m", "compileall", "-q", str(self.root / "buster")], 180)
            elif step in {"test", "behavioral_test", "verify"}:
                raw = self._run_command(["python", "-m", "pytest", "-q"], 900)
            elif step == "learn":
                raw = {"success": True, "message": "Learning step recorded."}
            else:
                raw = self._run_agent(agent, step, payload)

            success, message, data = self._normalise(raw)
            return StepResult(
                step=step,
                success=success,
                status="completed" if success else "failed",
                agent=agent,
                message=message,
                data=data,
                started_at=started,
                finished_at=utc_now(),
            )
        except Exception as exc:
            return StepResult(
                step=step,
                success=False,
                status="failed",
                agent=agent,
                message=str(exc),
                data={"traceback": traceback.format_exc()},
                started_at=started,
                finished_at=utc_now(),
            )

    def _run_agent(self, agent: str, step: str, payload: Dict[str, Any]) -> Any:
        if self.runtime_core is None:
            return {"success": False, "message": f"No runtime handler for '{step}'."}
        if agent and hasattr(self.runtime_core, "run_agent"):
            return self.runtime_core.run_agent(
                agent,
                {
                    "action": step,
                    "request": payload["job"]["request"],
                    "project": payload["job"]["project"],
                    "project_type": payload["job"]["project_type"],
                    "strategy": payload["strategy"],
                    "context": payload["context"],
                    "root": payload["root"],
                },
            )
        if hasattr(self.runtime_core, "run"):
            return self.runtime_core.run(f"Autonomy step '{step}': {payload['job']['request']}")
        return {"success": False, "message": f"Runtime cannot execute '{step}'."}

    def _fix_loop(
        self,
        job: AutonomyJob,
        strategy: Strategy,
        context: Dict[str, Any],
        result: ExecutionResult,
    ) -> bool:
        for attempt in range(1, self.max_fix_attempts + 1):
            fix_result = self._run_step(
                "fix_if_needed",
                job,
                strategy,
                {**context, "fix_attempt": attempt, "previous_steps": result.steps[-3:]},
            )
            result.steps.append(fix_result.to_dict())
            if not fix_result.success:
                continue
            test_result = self._run_step("test", job, strategy, {**context, "fix_attempt": attempt})
            result.steps.append(test_result.to_dict())
            if test_result.success:
                return True
        return False

    def _run_command(self, command: List[str], timeout: int) -> Dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": completed.returncode == 0,
            "message": "Command passed." if completed.returncode == 0 else "Command failed.",
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-12000:],
            "stderr": completed.stderr[-12000:],
        }

    @staticmethod
    def _normalise(raw: Any) -> tuple[bool, str, Dict[str, Any]]:
        if raw is None:
            return True, "Step completed.", {}
        if isinstance(raw, bool):
            return raw, "Step completed." if raw else "Step failed.", {}
        if isinstance(raw, str):
            lowered = raw.lower()
            failed = any(token in lowered for token in ("failed", "error:", "traceback", "exception"))
            return not failed, raw, {"output": raw}
        if isinstance(raw, Mapping):
            success = bool(raw.get("success", raw.get("ok", raw.get("status") not in {"failed", "error"})))
            message = str(raw.get("message", raw.get("summary", raw.get("output", "Step completed."))))
            return success, message, dict(raw)
        return True, str(raw), {"output": raw}

    def _complete_job(self, job: AutonomyJob, success: bool, result: ExecutionResult) -> None:
        if self.autonomy_engine is None or not hasattr(self.autonomy_engine, "complete_job"):
            return
        payload = {
            "execution": result.to_dict(),
            "what_worked": [step["step"] for step in result.steps if step.get("success")] if success else [],
            "what_failed": result.errors if not success else [],
            "fixes": [step.get("message", "") for step in result.steps if step.get("step") == "fix_if_needed" and step.get("success")],
            "reusable_patterns": [result.strategy],
        }
        try:
            self.autonomy_engine.complete_job(job.job_id, success, payload)
        except KeyError:
            pass

    def _finish(self, result: ExecutionResult) -> ExecutionResult:
        result.finished_at = utc_now()
        history = self._history()
        history.append(result.to_dict())
        self.history_path.write_text(json.dumps(history[-500:], indent=2, default=str), encoding="utf-8")
        return result

    def _history(self) -> List[Dict[str, Any]]:
        try:
            raw = json.loads(self.history_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except Exception:
            return []

    def _resolve(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    def _has_tests(self) -> bool:
        return (self.root / "tests").exists() or any(self.root.glob("test_*.py")) or any(self.root.glob("*_test.py"))
