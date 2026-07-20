from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .mode_selector import ModeSelector
from .execution_card import ExecutionCard
from .findings_table import FindingsTable
from .job_queue import JobQueue
from .history_panel import HistoryPanel
from .project_health_card import ProjectHealthCard
from .finding_details_panel import FindingDetailsPanel
from .apply_changes_worker import ApplyChangesWorker
from .code_review_worker import CodeReviewWorker
from .diff_generator import DiffGenerator
from .preview_diff_panel import PreviewDiff
from .preview_diff_worker import PreviewDiffWorker

from PySide6.QtCore import QThreadPool

from buster.ui.v9.panels.self_improvement.verification.verification_worker import (
    VerificationWorker,
)



class _SelfImprovementWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, runtime_core: Any, mode: str) -> None:
        super().__init__()
        self.runtime_core = runtime_core
        self.mode = mode

    @Slot()
    def run(self) -> None:
        try:
            runner = getattr(self.runtime_core, "run_self_improvement", None)

            if not callable(runner):
                raise RuntimeError(
                    "Runtime core does not provide run_self_improvement()."
                )

            try:
                result = runner(mode=self.mode)
            except TypeError:
                result = runner()

            self.finished.emit(result)

        except Exception as exc:
            self.failed.emit(str(exc))


class SelfImprovementPanel(QFrame):
    """
    Main Self Improvement workspace.

    Long-running scans execute in a QThread so the interface remains
    responsive.
    """

    def __init__(
        self,
        runtime_core=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self._scan_thread: Optional[QThread] = None
        self._scan_worker: Optional[_SelfImprovementWorker] = None

        self._review_thread: Optional[QThread] = None
        self._review_worker = None

        self._plan_thread: Optional[QThread] = None
        self._plan_worker = None

        self._preview_thread: Optional[QThread] = None
        self._preview_worker: Optional[PreviewDiffWorker] = None

        self._apply_thread: Optional[QThread] = None
        self._apply_worker: Optional[ApplyChangesWorker] = None

        self._current_finding: dict[str, Any] | None = None
        self._current_review: dict[str, Any] | None = None
        self._current_plan: dict[str, Any] | None = None
        self._current_preview: PreviewDiff | None = None
        self._rewarded_verifications: set[str] = set()
        self._verification_worker = None

        self.setObjectName("SelfImprovementPanel")

        self._build_ui()
        self._apply_styles()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_cached_state)
        self.timer.start(5000)

        QTimer.singleShot(0, self.refresh_cached_state)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        header = QHBoxLayout()

        title = QLabel("SELF IMPROVEMENT", self)
        title.setObjectName("SelfImprovementTitle")
        header.addWidget(title)

        self.status_label = QLabel("Ready", self)
        self.status_label.setObjectName("SelfImprovementStatus")
        header.addWidget(self.status_label)

        header.addStretch(1)

        self.scan_button = QPushButton("Run Scan", self)
        self.scan_button.clicked.connect(self.run_scan)
        header.addWidget(self.scan_button)

        root.addLayout(header)

        self.mode_selector = ModeSelector(
            runtime_core=self.runtime_core,
            parent=self,
        )
        root.addWidget(self.mode_selector)

        self.execution_card = ExecutionCard(
            runtime_core=self.runtime_core,
            parent=self,
        )
        root.addWidget(self.execution_card)

        self.health_card = ProjectHealthCard(self)
        root.addWidget(self.health_card)

        self.tabs = QTabWidget(self)

        self.findings = FindingsTable(
            runtime_core=self.runtime_core,
            parent=self,
        )

        self.finding_details = FindingDetailsPanel(self)
        self.finding_details.review_requested.connect(
            self._review_finding
        )
        self.finding_details.plan_requested.connect(
            self._plan_finding
        )
        self.finding_details.fix_requested.connect(
            self._preview_finding
        )
        self.finding_details.ignore_requested.connect(
            self._ignore_finding
        )
        self.finding_details.apply_requested.connect(
            self._apply_preview
        )
        self.finding_details.verify_requested.connect(
            self._verify_preview
        )
        self.finding_details.reject_requested.connect(
            self._reject_preview
        )
        self.finding_details.copy_patch_requested.connect(
            self._copy_patch
        )

        self.findings.finding_selected.connect(
            self._select_finding
        )
        self.findings.finding_activated.connect(
            self._select_finding
        )

        findings_page = QWidget(self)
        findings_layout = QVBoxLayout(findings_page)
        findings_layout.setContentsMargins(0, 0, 0, 0)

        findings_splitter = QSplitter(
            Qt.Orientation.Horizontal,
            findings_page,
        )
        findings_splitter.addWidget(self.findings)
        findings_splitter.addWidget(self.finding_details)
        findings_splitter.setStretchFactor(0, 3)
        findings_splitter.setStretchFactor(1, 2)
        findings_splitter.setSizes([760, 440])

        findings_layout.addWidget(findings_splitter)

        self.jobs = JobQueue(
            runtime_core=self.runtime_core,
            parent=self,
        )

        self.history = HistoryPanel(
            runtime_core=self.runtime_core,
            parent=self,
        )

        self.tabs.addTab(findings_page, "Findings")
        self.tabs.addTab(self.jobs, "Jobs")
        self.tabs.addTab(self.history, "History")

        root.addWidget(self.tabs, 1)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementPanel {
                background-color: #10151d;
                border: 1px solid #263241;
                border-radius: 12px;
            }

            QLabel#SelfImprovementTitle {
                color: #23B8FF;
                font-size: 15px;
                font-weight: 800;
            }

            QLabel#SelfImprovementStatus {
                color: #94a3b8;
                font-size: 11px;
                padding-left: 8px;
            }

            QPushButton {
                background-color: #1f2937;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #2563eb;
            }

            QPushButton:disabled {
                background-color: #18202b;
                color: #64748b;
                border-color: #263241;
            }
            """
        )

    @Slot()
    def run_scan(self) -> None:
        if self.runtime_core is None:
            self.status_label.setText("Runtime unavailable")
            return

        if self._scan_thread is not None and self._scan_thread.isRunning():
            return

        mode = self._current_mode()

        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")
        self.status_label.setText(f"Running {mode} scan")

        try:
            self.execution_card.start_scan(mode)
        except Exception:
            pass

        self._scan_thread = QThread(self)
        self._scan_worker = _SelfImprovementWorker(
            self.runtime_core,
            mode,
        )
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._scan_finished)
        self._scan_worker.failed.connect(self._scan_failed)

        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.failed.connect(self._scan_thread.quit)

        self._scan_thread.finished.connect(self._cleanup_scan_thread)
        self._scan_thread.start()

    @Slot(object)
    def _scan_finished(self, result: Any) -> None:
        self.status_label.setText("Scan completed")
        self._apply_scan_result(result)

        try:
            self.execution_card.show_scan_result(result)
        except Exception:
            pass

        self.refresh_cached_state()

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self.status_label.setText(f"Scan failed: {message}")

        try:
            self.execution_card.fail_scan(message)
        except Exception:
            pass

    @Slot()
    def _cleanup_scan_thread(self) -> None:
        if self._scan_worker is not None:
            self._scan_worker.deleteLater()

        if self._scan_thread is not None:
            self._scan_thread.deleteLater()

        self._scan_worker = None
        self._scan_thread = None

        self.scan_button.setEnabled(True)
        self.scan_button.setText("Run Scan")

    def refresh(self) -> None:
        self.refresh_cached_state()

    @Slot()
    def refresh_cached_state(self) -> None:
        """
        Read existing runtime state only.

        This does not call SelfImprovementService.scan(), because running
        that work on the Qt UI thread can freeze the application.
        """
        self._refresh_findings_from_status()

        try:
            self.jobs.refresh()
        except Exception:
            pass

        try:
            self.history.refresh()
        except Exception:
            pass

        try:
            if self._scan_thread is None:
                self.execution_card.refresh_from_runtime_status()
        except Exception:
            pass
    
    @Slot(object)
    def _review_finished(self, result: Any) -> None:
        if hasattr(result, "to_dict"):
            result = result.to_dict()
    
        self._current_review = result    

        if not isinstance(result, dict):
            self.finding_details.set_action_output(str(result))
            self.finding_details.set_busy(False)
            return

        self.finding_details.show_review(result)


    @Slot(str)
    def _review_failed(self, message: str) -> None:
        self.finding_details.set_action_output(
            f"AI Code Review failed:\n{message}"
        )
        self.finding_details.set_busy(False)


    @Slot()
    def _cleanup_review_thread(self) -> None:
        if self._review_worker is not None:
            self._review_worker.deleteLater()

        if self._review_thread is not None:
            self._review_thread.deleteLater()

        self._review_worker = None
        self._review_thread = None   

    @Slot(object)
    def _plan_finished(self, result: Any) -> None:
        self.finding_details.set_busy(False)

        if hasattr(result, "to_dict"):
            result = result.to_dict()

        if not isinstance(result, dict):
            self.finding_details.set_action_output(str(result))
            return

        self._current_plan = dict(result)
        self._current_preview = None
        self.finding_details.show_plan(result)


    @Slot(str)
    def _plan_failed(self, message: str) -> None:
        self.finding_details.set_busy(False)
        self.finding_details.set_action_output(
            f"Repair Planner failed:\n{message}"
        )


    @Slot()
    def _cleanup_plan_thread(self) -> None:
        if self._plan_worker is not None:
            self._plan_worker.deleteLater()

        if self._plan_thread is not None:
            self._plan_thread.deleteLater()

        self._plan_worker = None
        self._plan_thread = None
    

    @Slot(object)
    def _preview_finished(self, result: Any) -> None:
        self.finding_details.set_preview_busy(False)

        try:
            preview = PreviewDiff.from_value(result)
        except Exception as exc:
            self._preview_failed(str(exc))
            return
        
        reward_key = self._verification_reward_key(preview)
        self._rewarded_verifications.discard(reward_key)


        self._current_preview = preview
        self.finding_details.show_diff(preview)
        self.status_label.setText("Preview ready for approval")

    @Slot(str)
    def _preview_failed(self, message: str) -> None:
        self.finding_details.set_preview_busy(False)
        self.finding_details.set_action_output(
            f"Preview generation failed:\n{message}"
        )
        self.status_label.setText("Preview generation failed")

    @Slot()
    def _cleanup_preview_thread(self) -> None:
        if self._preview_worker is not None:
            self._preview_worker.deleteLater()

        if self._preview_thread is not None:
            self._preview_thread.deleteLater()

        self._preview_worker = None
        self._preview_thread = None

    @Slot(object)
    def _apply_finished(self, result: Any) -> None:
        self.finding_details.set_preview_busy(False)

        message = "Changes applied successfully."
        if isinstance(result, dict):
            message = str(
                result.get("message")
                or result.get("summary")
                or message
            )
        elif result not in (None, True):
            message = str(result)

        self.finding_details.set_action_output(message)
        self.status_label.setText("Changes applied; verifying")
        self._verify_preview(self._current_preview)

    @Slot(str)
    def _apply_failed(self, message: str) -> None:
        self.finding_details.set_preview_busy(False)
        self.finding_details.set_preview_validation(
            "invalid",
            message,
        )
        recorder = getattr(
            self.runtime_core,
            "record_evolution_action",
            None,
        )

        if callable(recorder):
            recorder(
                "repair",
                success=False,
            )
        
        
        self.finding_details.set_action_output(
            f"Could not apply the approved patch:\n{message}"
        )
        self.status_label.setText("Apply failed")

    @Slot()
    def _cleanup_apply_thread(self) -> None:
        if self._apply_worker is not None:
            self._apply_worker.deleteLater()

        if self._apply_thread is not None:
            self._apply_thread.deleteLater()

        self._apply_worker = None
        self._apply_thread = None

    def _refresh_findings_from_status(self) -> None:
        status = self._get_self_improvement_status()

        if not isinstance(status, dict):
            return

        last_cycle = status.get("last_cycle")

        findings = (
            status.get("findings")
            or status.get("latest_findings")
            or status.get("results")
            or (
                last_cycle.get("findings", [])
                if isinstance(last_cycle, dict)
                else []
            )
        )

        if isinstance(findings, list):
            self.findings.set_findings(findings)
            self.health_card.set_findings(findings)

            if not findings:
                self._current_finding = None
                self._current_review = None
                self._current_plan = None
                self._current_preview = None
                self.finding_details.clear()

        state = (
            status.get("state")
            or status.get("status")
            or status.get("mode")
        )

        if state and self._scan_thread is None:
            self.status_label.setText(str(state).replace("_", " ").title())

    def _get_self_improvement_status(self) -> dict[str, Any]:
        if self.runtime_core is None:
            return {}

        helper = getattr(
            self.runtime_core,
            "self_improvement_status",
            None,
        )

        if callable(helper):
            try:
                value = helper()
                return value if isinstance(value, dict) else {}
            except Exception:
                return {}

        service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )

        status = getattr(service, "status", None)

        if callable(status):
            try:
                value = status()
                return value if isinstance(value, dict) else {}
            except Exception:
                return {}

        return {}

    def _apply_scan_result(self, result: Any) -> None:
        if hasattr(result, "to_dict") and callable(result.to_dict):
            try:
                result = result.to_dict()
            except Exception:
                return

        if isinstance(result, list):
            self.findings.set_findings(result)
            return

        if not isinstance(result, dict):
            return

        findings = (
            result.get("findings")
            or result.get("latest_findings")
            or result.get("results")
            or []
        )

        if isinstance(findings, list):
            self.findings.set_findings(findings)

    @Slot(dict)
    def _select_finding(self, finding: dict[str, Any]) -> None:
        """
        Select a finding and reset any review cached for a different item.
        """
        selected = dict(finding)

        if selected != self._current_finding:
            self._current_review = None
            self._current_plan = None
            self._current_preview = None

        self._current_finding = selected
        self.finding_details.set_finding(selected)

    @Slot(dict)
    def _review_finding(self, finding: dict[str, Any]) -> None:
        if self._review_thread is not None and self._review_thread.isRunning():
            return

        self._current_finding = dict(finding)
        self._current_review = None
        self._current_plan = None
        self._current_preview = None

        ai_manager = getattr(self.runtime_core, "ai_manager", None)
        if ai_manager is None:
            self.finding_details.set_action_output(
                "AI Code Review is unavailable because the shared "
                "AI provider manager is not connected."
            )
            return

        try:
            from buster.autonomy.code_review_service import (
                CodeReviewService,
            )

            service = CodeReviewService(
                root=getattr(self.runtime_core, "root", "."),
                ai_manager=ai_manager,
                dispatcher=getattr(
                    self.runtime_core,
                    "dispatcher",
                    None,
                ),
            )

            self.finding_details.set_busy(
                True,
                "Analysing in background..."
            )

            self._review_thread = QThread(self)
            self._review_worker = CodeReviewWorker(
                service,
                finding,
            )
            self._review_worker.moveToThread(
                self._review_thread
            )

            self._review_thread.started.connect(
                self._review_worker.run
            )
            self._review_worker.finished.connect(
                self._review_finished
            )
            self._review_worker.failed.connect(
                self._review_failed
            )
            self._review_worker.finished.connect(
                self._review_thread.quit
            )
            self._review_worker.failed.connect(
                self._review_thread.quit
            )
            self._review_thread.finished.connect(
                self._cleanup_review_thread
            )

            self._review_thread.start()

        except Exception as exc:
            self.finding_details.set_busy(False)
            self.finding_details.set_action_output(
                f"AI Code Review could not start:\n{exc}"
            )

    @Slot(dict)
    def _plan_finding(self, finding: dict[str, Any]) -> None:
        """
        Generate a structured repair plan for the currently selected finding.

        Requires an AI review to have been completed first.
        """

        if self._plan_thread is not None and self._plan_thread.isRunning():
            return

        review = self._current_review

        if not review:
            self.finding_details.set_action_output(
                "Run an AI Review before requesting a repair plan."
            )
            return

        if self._current_finding is None or finding != self._current_finding:
            self.finding_details.set_action_output(
                "Please run an AI Review for the currently selected finding "
                "before generating its repair plan."
            )
            return

        plan_finding = dict(self._current_finding)
        plan_review = dict(review)

        ai_manager = getattr(self.runtime_core, "ai_manager", None)
        if ai_manager is None:
            self.finding_details.set_action_output(
                "Repair Planner is unavailable because the AI provider "
                "manager is not connected."
            )
            return

        try:
            from buster.autonomy.repair_planner import RepairPlanner
            from .repair_plan_worker import RepairPlanWorker

            planner = RepairPlanner(
                root=getattr(self.runtime_core, "root", "."),
                ai_manager=ai_manager,
                dispatcher=getattr(
                    self.runtime_core,
                    "dispatcher",
                    None,
                ),
            )

            self.finding_details.set_busy(
                True,
                "Planning repair strategy..."
            )

            self._plan_thread = QThread(self)

            self._plan_worker = RepairPlanWorker(
                planner,
                plan_finding,
                plan_review,
            )

            self._plan_worker.moveToThread(
                self._plan_thread
            )

            self._plan_thread.started.connect(
                self._plan_worker.run
            )

            self._plan_worker.finished.connect(
                self._plan_finished
            )

            self._plan_worker.failed.connect(
                self._plan_failed
            )

            self._plan_worker.finished.connect(
                self._plan_thread.quit
            )

            self._plan_worker.failed.connect(
                self._plan_thread.quit
            )

            self._plan_thread.finished.connect(
                self._cleanup_plan_thread
            )

            self._plan_thread.start()

        except Exception as exc:
            self.finding_details.set_busy(False)
            self.finding_details.set_action_output(
                f"Repair Planner could not start:\n{exc}"
            )

    @Slot(dict)
    def _preview_finding(self, finding: dict[str, Any]) -> None:
        if (
            self._preview_thread is not None
            and self._preview_thread.isRunning()
        ):
            return

        if not self._current_plan:
            self.finding_details.set_action_output(
                "Generate a Repair Plan before requesting a preview."
            )
            return

        if (
            self._current_finding is None
            or dict(finding) != self._current_finding
        ):
            self.finding_details.set_action_output(
                "The repair plan does not belong to the currently selected "
                "finding. Run AI Review and Repair Plan again."
            )
            return

        provider = self._resolve_diff_provider()
        generator = DiffGenerator(
            project_root=getattr(self.runtime_core, "root", "."),
            provider=provider,
        )

        self._current_preview = None
        self.finding_details.set_preview_busy(
            True,
            "Generating preview diff...",
        )
        self.status_label.setText("Generating preview")

        self._preview_thread = QThread(self)
        self._preview_worker = PreviewDiffWorker(
            generator=generator,
            finding=dict(self._current_finding),
            review=dict(self._current_review or {}),
            plan=dict(self._current_plan),
            context={
                "requested_from": "self_improvement_ui",
                "approval_required": True,
            },
        )
        self._preview_worker.moveToThread(
            self._preview_thread
        )

        self._preview_thread.started.connect(
            self._preview_worker.run
        )
        self._preview_worker.progress.connect(
            self._preview_progress
        )
        self._preview_worker.finished.connect(
            self._preview_finished
        )
        self._preview_worker.failed.connect(
            self._preview_failed
        )
        self._preview_worker.finished.connect(
            self._preview_thread.quit
        )
        self._preview_worker.failed.connect(
            self._preview_thread.quit
        )
        self._preview_thread.finished.connect(
            self._cleanup_preview_thread
        )
        self._preview_thread.start()

    @Slot(int, str)
    def _preview_progress(self, value: int, message: str) -> None:
        del value
        self.status_label.setText(message)

    @Slot(object)
    def _apply_preview(self, value: Any) -> None:
        if (
            self._apply_thread is not None
            and self._apply_thread.isRunning()
        ):
            return

        preview = PreviewDiff.from_value(
            value if value is not None else self._current_preview
        )

        if not preview.patch.strip():
            self.finding_details.set_action_output(
                "There is no generated patch to apply."
            )
            return

        applier = self._resolve_patch_applier()
        if applier is None:
            self.finding_details.set_action_output(
                "Apply is unavailable because no patch applier is "
                "connected to the runtime."
            )
            return

        self._current_preview = preview
        self.finding_details.set_preview_busy(
            True,
            "Applying approved changes...",
        )
        self.finding_details.set_preview_validation(
            "running",
            "Applying the approved patch.",
        )
        self.status_label.setText("Applying approved changes")

        self._apply_thread = QThread(self)
        self._apply_worker = ApplyChangesWorker(
            applier=applier,
            preview=preview,
            backup=True,
        )
        self._apply_worker.moveToThread(self._apply_thread)

        self._apply_thread.started.connect(
            self._apply_worker.run
        )
        self._apply_worker.progress.connect(
            self._apply_progress
        )
        self._apply_worker.finished.connect(
            self._apply_finished
        )
        self._apply_worker.failed.connect(
            self._apply_failed
        )
        self._apply_worker.finished.connect(
            self._apply_thread.quit
        )
        self._apply_worker.failed.connect(
            self._apply_thread.quit
        )
        self._apply_thread.finished.connect(
            self._cleanup_apply_thread
        )
        self._apply_thread.start()

    @Slot(int, str)
    def _apply_progress(self, value: int, message: str) -> None:
        del value
        self.status_label.setText(message)

    @Slot(object)
    def _verify_preview(self, value: Any = None) -> None:
        preview = PreviewDiff.from_value(
            value if value is not None else self._current_preview
        )

        if not preview.patch.strip():
            self.finding_details.set_action_output(
                "There is no preview available to verify."
            )
            return

        file_path = str(preview.file_path or "").strip()

        if not file_path:
            self.finding_details.set_preview_validation(
                "invalid",
                "The preview does not identify a file to verify.",
            )
            self.finding_details.set_action_output(
                "Verification cannot run because this preview has no file path."
            )
            self.status_label.setText("Verification failed")
            return

        if self._verification_worker is not None:
            self.finding_details.set_action_output(
                "Verification is already running."
            )
            return

        self._current_preview = preview

        self.finding_details.set_preview_busy(
            True,
            "Running verification...",
        )
        self.finding_details.set_preview_validation(
            "running",
            "Running verification in the background...",
        )
        self.status_label.setText("Running verification")
        
        print("VERIFY FILE:", repr(file_path))
        print("PROJECT ROOT:", self.runtime_core.root)

        worker = VerificationWorker(
            project_root=self.runtime_core.root,
            files=[file_path],
            change_id=str(
                preview.metadata.get("change_id", "")
            ),
        )

        worker.signals.progress.connect(
            self._verification_progress
        )
        worker.signals.finished.connect(
            lambda report, p=preview: self._verification_finished(
                report,
                p,
            )
        )
        worker.signals.failed.connect(
            lambda message, p=preview: self._verification_failed(
                message,
                p,
            )
        )

        self._verification_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _verification_reward_key(
        self,
        preview: PreviewDiff,
    ) -> str:
        change_id = str(
            getattr(preview, "change_id", "") or ""
        ).strip()

        if change_id:
            return change_id

        file_path = str(
            getattr(preview, "file_path", "") or ""
        ).strip()

        patch = str(
            getattr(preview, "patch", "") or ""
        )

        return f"{file_path}:{hash(patch)}"
        
    @Slot(str)
    def _verification_progress(self, message: str) -> None:
        self.status_label.setText(str(message))


    def _verification_finished(
        self,
        report: Any,
        preview: PreviewDiff,
    ) -> None:
        self.finding_details.set_preview_busy(False)

        passed, message = self._normalise_verification_result(
            report
        )

        recorder = getattr(
            self.runtime_core,
            "record_evolution_action",
            None,
        )

        reward_key = self._verification_reward_key(preview)

        if reward_key not in self._rewarded_verifications:
            if callable(recorder):
                recorder(
                    "repair",
                    success=passed,
                )

            self._rewarded_verifications.add(reward_key)

        self.finding_details.set_preview_validation(
            "valid" if passed else "invalid",
            message,
        )
        self.finding_details.set_action_output(message)

        self.status_label.setText(
            "Verification passed"
            if passed
            else "Verification failed"
        )

        self._verification_worker = None


    def _verification_failed(
        self,
        message: str,
        preview: PreviewDiff,
    ) -> None:
        self.finding_details.set_preview_busy(False)

        self.finding_details.set_preview_validation(
            "invalid",
            str(message),
        )
        self.finding_details.set_action_output(
            f"Verification failed:\n{message}"
        )
        self.status_label.setText("Verification failed")

        recorder = getattr(
            self.runtime_core,
            "record_evolution_action",
            None,
        )

        reward_key = self._verification_reward_key(preview)

        if reward_key not in self._rewarded_verifications:
            if callable(recorder):
                recorder(
                    "repair",
                    success=False,
                )

            self._rewarded_verifications.add(reward_key)

        self._verification_worker = None    

    @Slot(object)
    def _reject_preview(self, value: Any) -> None:
        del value
        self._current_preview = None
        self.status_label.setText("Preview rejected; no files changed")

    @Slot(object)
    def _copy_patch(self, value: Any) -> None:
        preview = PreviewDiff.from_value(
            value if value is not None else self._current_preview
        )

        if not preview.patch:
            self.finding_details.set_action_output(
                "There is no patch to copy."
            )
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(preview.patch)
        self.status_label.setText("Patch copied to clipboard")

    def _resolve_diff_provider(self) -> Any:
        candidates = (
            getattr(self.runtime_core, "diff_generator", None),
            getattr(self.runtime_core, "code_generator", None),
            getattr(self.runtime_core, "ai_manager", None),
            getattr(
                getattr(self.runtime_core, "self_improvement", None),
                "diff_generator",
                None,
            ),
        )

        for candidate in candidates:
            if candidate is not None:
                return candidate

        return None

    def _resolve_patch_applier(self) -> Any:
        scan_service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )

        repair_service = getattr(
            self.runtime_core,
            "self_improvement_service",
            None,
        )

        repair_adapter = getattr(
            repair_service,
            "runtime_adapter",
            None,
        )

        candidates = (
            getattr(self.runtime_core, "patch_applier", None),
            getattr(self.runtime_core, "apply_changes", None),

            getattr(scan_service, "patch_applier", None),
            getattr(scan_service, "apply_changes", None),
            getattr(scan_service, "apply_patch", None),

            getattr(repair_service, "patch_applier", None),
            getattr(repair_service, "apply_changes", None),
            getattr(repair_service, "apply_patch", None),

            getattr(repair_adapter, "patch_applier", None),
            getattr(repair_adapter, "apply_changes", None),
            getattr(repair_adapter, "apply_patch", None),
        )

        for candidate in candidates:
            if candidate is not None:
                return candidate

        try:
            from buster.ui.v9.panels.self_improvement.patch_applier import (
                PatchApplier,
            )

            return PatchApplier(
                project_root=getattr(
                    self.runtime_core,
                    "root",
                    ".",
                )
            )
        except Exception:
            return None

    def _resolve_verifier(self) -> Any:
        service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )

        candidates = (
            getattr(self.runtime_core, "verify_changes", None),
            getattr(self.runtime_core, "verification_service", None),
            getattr(service, "verify_changes", None),
            getattr(service, "verify_patch", None),
            getattr(service, "verification_service", None),
        )

        for candidate in candidates:
            if candidate is not None:
                return candidate

        return None

    @staticmethod
    def _invoke_verifier(verifier: Any, preview: PreviewDiff) -> Any:
        if callable(verifier):
            method = verifier
        else:
            method = None
            for name in (
                "verify",
                "verify_changes",
                "verify_patch",
                "run",
            ):
                candidate = getattr(verifier, name, None)
                if callable(candidate):
                    method = candidate
                    break

        if method is None:
            raise RuntimeError(
                "Verification service exposes no supported method."
            )

        attempts = (
            lambda: method(preview=preview),
            lambda: method(
                patch=preview.patch,
                file_path=preview.file_path,
            ),
            lambda: method(preview),
            lambda: method(preview.patch),
            lambda: method(),
        )

        last_error = None
        for attempt in attempts:
            try:
                return attempt()
            except TypeError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

        raise RuntimeError("Could not invoke verification service.")

    @staticmethod
    def _normalise_verification_result(
        result: Any,
    ) -> tuple[bool, str]:
        if isinstance(result, bool):
            return (
                result,
                "Verification passed."
                if result
                else "Verification failed.",
            )

        if hasattr(result, "to_dict") and callable(result.to_dict):
            result = result.to_dict()

        if isinstance(result, dict):
            passed = bool(
                result.get("passed")
                if "passed" in result
                else result.get("success")
                if "success" in result
                else result.get("valid")
            )
            message = str(
                result.get("message")
                or result.get("summary")
                or (
                    "Verification passed."
                    if passed
                    else "Verification failed."
                )
            )
            return passed, message

        text = str(result or "").strip()
        lowered = text.lower()
        passed = not any(
            word in lowered
            for word in ("fail", "error", "invalid")
        )
        return passed, text or (
            "Verification passed."
            if passed
            else "Verification failed."
        )

    @Slot(dict)
    def _ignore_finding(self, finding: dict[str, Any]) -> None:
        service = getattr(self.runtime_core, "self_improvement", None)
        ignore = getattr(service, "ignore_finding", None)

        if not callable(ignore):
            self.finding_details.set_action_output(
                "Ignore is unavailable because the service does not "
                "support persistent suppression."
            )
            return

        try:
            ignore(finding)
        except Exception as exc:
            self.finding_details.set_action_output(
                f"Could not ignore this finding:\n{exc}"
            )
            return

        remaining = [
            item
            for item in self.findings.findings
            if not (
                item.get("category") == finding.get("category")
                and item.get("title") == finding.get("title")
                and item.get("file") == finding.get("file")
                and item.get("line") == finding.get("line")
            )
        ]

        self.findings.set_findings(remaining)
        self.health_card.set_findings(remaining)
        self._current_finding = None
        self._current_review = None
        self._current_plan = None
        self._current_preview = None
        self.finding_details.clear()
        self.status_label.setText(
            "Finding ignored until its source file changes"
        )

    def _current_mode(self) -> str:
        selector = self.mode_selector

        for name in ("current_mode", "mode", "selected_mode"):
            value = getattr(selector, name, None)

            if callable(value):
                try:
                    value = value()
                except Exception:
                    continue

            if isinstance(value, str) and value:
                return value.lower()

        service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )
        value = getattr(service, "mode", None)

        if isinstance(value, str) and value:
            return value.lower()

        return "manual"

    def set_runtime_core(self, runtime_core) -> None:
        self.runtime_core = runtime_core

        if hasattr(self.mode_selector, "set_runtime_core"):
            self.mode_selector.set_runtime_core(runtime_core)

        if hasattr(self.execution_card, "set_runtime_core"):
            self.execution_card.set_runtime_core(runtime_core)

        self.findings.runtime_core = runtime_core
        self.jobs.runtime_core = runtime_core
        self.history.runtime_core = runtime_core

        self.refresh_cached_state()

    def closeEvent(self, event) -> None:
        if self.timer.isActive():
            self.timer.stop()

        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.quit()
            self._scan_thread.wait(1500)
    
        if (
            self._review_thread is not None
            and self._review_thread.isRunning()
        ):
            self._review_thread.quit()
            self._review_thread.wait(1500)

        if (
            self._plan_thread is not None
            and self._plan_thread.isRunning()
        ):
            self._plan_thread.quit()
            self._plan_thread.wait(1500)

        if (
            self._preview_thread is not None
            and self._preview_thread.isRunning()
        ):
            if self._preview_worker is not None:
                self._preview_worker.cancel()
            self._preview_thread.quit()
            self._preview_thread.wait(1500)

        if (
            self._apply_thread is not None
            and self._apply_thread.isRunning()
        ):
            if self._apply_worker is not None:
                self._apply_worker.cancel()
            self._apply_thread.quit()
            self._apply_thread.wait(1500)

        super().closeEvent(event)


__all__ = [
    "SelfImprovementPanel",
]
