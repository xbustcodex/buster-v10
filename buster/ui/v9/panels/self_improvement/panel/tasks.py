from __future__ import annotations

import logging
from typing import Any, Callable, Optional
from PySide6.QtCore import QThreadPool, QThread, QObject

from .runner import run_async_task
from .service_resolver import ServiceResolver
from ..code_review_worker import CodeReviewWorker
from ..diff_generator import DiffGenerator
from ..preview_diff_worker import PreviewDiffWorker
from ..apply_changes_worker import ApplyChangesWorker

logger = logging.getLogger(__name__)


class TaskController:
    """Manages asynchronous workflows for scanning, reviewing, and applying changes."""

    def __init__(self, panel: Any) -> None:
        self.panel = panel

    @property
    def runtime_core(self) -> Any:
        return self.panel.runtime_core

    def run_scan(self, mode: str, on_finished: Callable[[Any], None], on_failed: Callable[[str], None]) -> None:
        def _scan_job():
            # 1. Check primary runtime_core (e.g. KernelRuntime)
            runner = getattr(self.runtime_core, "run_self_improvement", None)
            
            # 2. Check cross-linked legacy core
            if not callable(runner):
                legacy = getattr(self.runtime_core, "legacy_core", None)
                if legacy:
                    runner = getattr(legacy, "run_self_improvement", None)

            # 3. Check registered services
            if not callable(runner):
                services = getattr(self.runtime_core, "services", None)
                if services:
                    svc = getattr(services, "get", lambda k: None)("self_improvement") or getattr(services, "get", lambda k: None)("self_healing")
                    if svc:
                        runner = getattr(svc, "run_self_improvement", None)

            # Execute if found
            if callable(runner):
                try:
                    return runner(mode=mode)
                except TypeError:
                    return runner()

            # Safe fallback response if no active scan engine is mounted
            logger.warning("No run_self_improvement() runner found across runtime cores/services. Returning idle state.")
            return {
                "status": "idle",
                "message": "Self-improvement scan engine initialized.",
                "findings": [],
            }

        run_async_task(_scan_job, on_finished, on_failed)

    def review_finding(self, finding: dict[str, Any], on_finished: Callable[[Any], None], on_failed: Callable[[str], None]) -> bool:
        ai_manager = getattr(self.runtime_core, "ai_manager", None)
        if ai_manager is None:
            return False

        try:
            from buster.autonomy.code_review_service import CodeReviewService

            service = CodeReviewService(
                root=getattr(self.runtime_core, "root", "."),
                ai_manager=ai_manager,
                dispatcher=getattr(self.runtime_core, "dispatcher", None),
            )
            
            thread = QThread(self.panel)
            worker = CodeReviewWorker(service, finding)
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            worker.finished.connect(on_finished)
            worker.failed.connect(on_failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(thread.deleteLater)
            
            thread.start()
            return True
        except Exception as exc:
            logger.exception("Failed to start review worker")
            on_failed(str(exc))
            return False

    def plan_finding(
        self,
        finding: dict[str, Any],
        review: dict[str, Any],
        on_finished: Callable[[Any], None],
        on_failed: Callable[[str], None],
    ) -> bool:
        ai_manager = getattr(self.runtime_core, "ai_manager", None)
        if ai_manager is None:
            return False

        try:
            from buster.autonomy.repair_planner import RepairPlanner
            from ..repair_plan_worker import RepairPlanWorker

            planner = RepairPlanner(
                root=getattr(self.runtime_core, "root", "."),
                ai_manager=ai_manager,
                dispatcher=getattr(self.runtime_core, "dispatcher", None),
            )
            
            thread = QThread(self.panel)
            worker = RepairPlanWorker(planner, finding, review)
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            worker.finished.connect(on_finished)
            worker.failed.connect(on_failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(thread.deleteLater)

            thread.start()
            return True
        except Exception as exc:
            logger.exception("Failed to start repair planner worker")
            on_failed(str(exc))
            return False

    def preview_finding(
        self,
        finding: dict[str, Any],
        review: dict[str, Any],
        plan: dict[str, Any],
        on_progress: Callable[[int, str], None],
        on_finished: Callable[[Any], None],
        on_failed: Callable[[str], None],
    ) -> None:
        provider = ServiceResolver.resolve_diff_provider(self.runtime_core)
        generator = DiffGenerator(
            project_root=getattr(self.runtime_core, "root", "."),
            provider=provider,
        )
        
        thread = QThread(self.panel)
        worker = PreviewDiffWorker(
            generator=generator,
            finding=finding,
            review=review,
            plan=plan,
            context={
                "requested_from": "self_improvement_ui",
                "approval_required": True,
                "agent_module": "buster.agents.python_agent",
            },
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        thread.start()

    def apply_preview(
        self,
        preview: Any,
        on_progress: Callable[[int, str], None],
        on_finished: Callable[[Any], None],
        on_failed: Callable[[str], None],
    ) -> bool:
        applier = ServiceResolver.resolve_patch_applier(self.runtime_core)
        if applier is None:
            return False

        thread = QThread(self.panel)
        worker = ApplyChangesWorker(applier=applier, preview=preview, backup=True)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        thread.start()
        return True

    def cleanup(self) -> None:
        """Cancel queued global tasks and wait for remaining background workers."""
        pool = QThreadPool.globalInstance()
        pool.clear()
        pool.waitForDone(1000)