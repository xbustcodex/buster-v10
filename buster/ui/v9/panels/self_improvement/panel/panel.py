from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QThreadPool, QTimer, Qt, Slot
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from .workspace import WorkspaceBuilder
from .tasks import TaskController
from .service_resolver import ServiceResolver
from ..preview_diff_panel import PreviewDiff
from buster.ui.v9.panels.self_improvement.verification.verification_worker import (
    VerificationWorker,
)

logger = logging.getLogger(__name__)


class SelfImprovementPanel(QFrame):
    """
    Modular Main Self Improvement Panel.
    Delegates workspace building to WorkspaceBuilder and task execution/threads
    to TaskController while managing user events and signal connections.
    """

    def __init__(self, runtime_core: Any = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self._is_findings_maximized = False
        self._is_scanning = False

        self._current_finding: Optional[dict[str, Any]] = None
        self._current_review: Optional[dict[str, Any]] = None
        self._current_plan: Optional[dict[str, Any]] = None
        self._current_preview: Optional[PreviewDiff] = None
        self._rewarded_verifications: set[str] = set()
        self._verification_worker: Optional[VerificationWorker] = None

        self.setObjectName("SelfImprovementPanel")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Build workspace UI layout & initialize task controller
        self.workspace = WorkspaceBuilder(self, runtime_core)
        self.workspace.build_layout()
        self.task_controller = TaskController(self)

        self._apply_styles()
        self._connect_signals()

        # Polling timer for status and finding refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_cached_state)
        self.timer.start(5000)

        QTimer.singleShot(0, self.refresh_cached_state)

    def _connect_signals(self) -> None:
        """Connect all UI workspace events to the panel handler actions."""
        w = self.workspace

        # Top bar controls
        w.expand_button.clicked.connect(self.toggle_findings_maximized)
        w.scan_button.clicked.connect(self.run_scan)

        # Findings table selection
        w.findings.finding_selected.connect(self._select_finding)
        w.findings.finding_activated.connect(self._select_finding)

        # Finding details panel actions
        w.finding_details.review_requested.connect(self._review_finding)
        w.finding_details.plan_requested.connect(self._plan_finding)
        w.finding_details.fix_requested.connect(self._preview_finding)
        w.finding_details.ignore_requested.connect(self._ignore_finding)
        w.finding_details.apply_requested.connect(self._apply_preview)
        w.finding_details.verify_requested.connect(self._verify_preview)
        w.finding_details.reject_requested.connect(self._reject_preview)
        w.finding_details.copy_patch_requested.connect(self._copy_patch)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self._is_findings_maximized:
            self.toggle_findings_maximized()
            event.accept()
            return
        super().keyPressEvent(event)

    @Slot()
    def toggle_findings_maximized(self) -> None:
        self._is_findings_maximized = not self._is_findings_maximized
        self.workspace.toggle_maximized(self._is_findings_maximized)

    @Slot()
    def run_scan(self) -> None:
        if self.runtime_core is None or self._is_scanning:
            return

        mode = self._current_mode()
        self._is_scanning = True
        self.workspace.scan_button.setEnabled(False)
        self.workspace.scan_button.setText("Scanning...")
        self.workspace.status_label.setText(f"Running {mode} scan")

        self.task_controller.run_scan(mode, self._scan_finished, self._scan_failed)

    @Slot(object)
    def _scan_finished(self, result: Any) -> None:
        self._is_scanning = False
        self.workspace.scan_button.setEnabled(True)
        self.workspace.scan_button.setText("Run Scan")
        self.workspace.status_label.setText("Scan completed")

        # Update ExecutionCard status if available
        if hasattr(self.workspace.execution_card, "update_status"):
            self.workspace.execution_card.update_status(result)

        # Extract findings directly from the scan result
        findings = []
        if hasattr(result, "to_dict") and callable(result.to_dict):
            try:
                result = result.to_dict()
            except Exception:
                pass

        if isinstance(result, list):
            findings = result
        elif isinstance(result, dict):
            findings = (
                result.get("findings")
                or result.get("latest_findings")
                or result.get("results")
                or result.get("active_findings")
                or []
            )
        elif hasattr(result, "findings"):
            findings = getattr(result, "findings", [])

        if findings:
            processed = self._process_raw_findings(findings)
            self.workspace.findings.set_findings(processed)
            self.workspace.health_card.set_findings(processed)

            # Persist findings back into runtime_core so polling preserves state
            if self.runtime_core is not None:
                setattr(self.runtime_core, "findings", processed)
                service = ServiceResolver.get_service(self.runtime_core)
                if service is not None:
                    setattr(service, "findings", processed)
        else:
            self.refresh_cached_state()

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self._is_scanning = False
        self.workspace.scan_button.setEnabled(True)
        self.workspace.scan_button.setText("Run Scan")
        self.workspace.status_label.setText(f"Scan failed: {message}")

    @Slot(dict)
    def _select_finding(self, finding: dict[str, Any]) -> None:
        selected = dict(finding)
        if selected != self._current_finding:
            self._current_review = None
            self._current_plan = None
            self._current_preview = None

        self._current_finding = selected
        self.workspace.finding_details.set_finding(selected)

    @Slot(dict)
    def _review_finding(self, finding: dict[str, Any]) -> None:
        self._current_finding = dict(finding)
        self._current_review = None
        self._current_plan = None
        self._current_preview = None

        self.workspace.finding_details.set_busy(True, "Analysing in background...")
        if not self.task_controller.review_finding(finding, self._review_finished, self._review_failed):
            self.workspace.finding_details.set_busy(False)
            self.workspace.finding_details.set_action_output("AI Review service unavailable.")

    @Slot(object)
    def _review_finished(self, result: Any) -> None:
        self.workspace.finding_details.set_busy(False)
        if hasattr(result, "to_dict"):
            result = result.to_dict()

        self._current_review = result if isinstance(result, dict) else None
        if isinstance(result, dict):
            self.workspace.finding_details.show_review(result)
        else:
            self.workspace.finding_details.set_action_output(str(result))

    @Slot(str)
    def _review_failed(self, message: str) -> None:
        self.workspace.finding_details.set_busy(False)
        self.workspace.finding_details.set_action_output(f"AI Code Review failed:\n{message}")

    @Slot(dict)
    def _plan_finding(self, finding: dict[str, Any]) -> None:
        if not self._current_review or self._current_finding != finding:
            self.workspace.finding_details.set_action_output("Run an AI Review for this finding first.")
            return

        self.workspace.finding_details.set_busy(True, "Planning repair strategy...")
        self.task_controller.plan_finding(finding, self._current_review, self._plan_finished, self._plan_failed)

    @Slot(object)
    def _plan_finished(self, result: Any) -> None:
        self.workspace.finding_details.set_busy(False)
        if hasattr(result, "to_dict"):
            result = result.to_dict()

        if isinstance(result, dict):
            self._current_plan = dict(result)
            self.workspace.finding_details.show_plan(result)

    @Slot(str)
    def _plan_failed(self, message: str) -> None:
        self.workspace.finding_details.set_busy(False)
        self.workspace.finding_details.set_action_output(f"Repair Planner failed:\n{message}")

    @Slot(dict)
    def _preview_finding(self, finding: dict[str, Any]) -> None:
        if not self._current_plan:
            self._current_plan = {"summary": f"Fix for {finding.get('title', 'Finding')}"}

        self.workspace.finding_details.set_preview_busy(True, "Generating preview diff...")
        self.workspace.status_label.setText("Generating preview")

        self.task_controller.preview_finding(
            finding,
            self._current_review or {},
            self._current_plan,
            lambda v, msg: self.workspace.status_label.setText(msg),
            self._preview_finished,
            self._preview_failed,
        )

    @Slot(object)
    def _preview_finished(self, result: Any) -> None:
        self.workspace.finding_details.set_preview_busy(False)
        preview = PreviewDiff.from_value(result)
        self._current_preview = preview
        self.workspace.finding_details.show_diff(preview)
        self.workspace.status_label.setText("Preview ready for approval")

    @Slot(str)
    def _preview_failed(self, message: str) -> None:
        self.workspace.finding_details.set_preview_busy(False)
        self.workspace.finding_details.set_action_output(f"Preview failed:\n{message}")
        self.workspace.status_label.setText("Preview failed")

    @Slot(object)
    def _apply_preview(self, value: Any) -> None:
        preview = PreviewDiff.from_value(value if value is not None else self._current_preview)
        if not preview.patch.strip():
            self.workspace.finding_details.set_action_output("No patch available to apply.")
            return

        self.workspace.finding_details.set_preview_busy(True, "Applying approved changes...")
        self.workspace.status_label.setText("Applying approved changes")

        self.task_controller.apply_preview(
            preview,
            lambda v, msg: self.workspace.status_label.setText(msg),
            self._apply_finished,
            self._apply_failed,
        )

    @Slot(object)
    def _apply_finished(self, result: Any) -> None:
        self.workspace.finding_details.set_preview_busy(False)
        self.workspace.status_label.setText("Changes applied; verifying...")
        self._verify_preview(self._current_preview)

    @Slot(str)
    def _apply_failed(self, message: str) -> None:
        self.workspace.finding_details.set_preview_busy(False)
        self.workspace.finding_details.set_action_output(f"Apply failed:\n{message}")
        self.workspace.status_label.setText("Apply failed")

    @Slot(object)
    def _verify_preview(self, value: Any = None) -> None:
        preview = PreviewDiff.from_value(value if value is not None else self._current_preview)
        file_path = str(preview.file_path or "").strip()

        if not file_path:
            self.workspace.finding_details.set_action_output("No file path specified for verification.")
            return

        if self._verification_worker is not None:
            self.workspace.finding_details.set_action_output("Verification is already in progress.")
            return

        self.workspace.finding_details.set_preview_busy(True, "Running verification...")
        self.workspace.status_label.setText("Running verification")

        worker = VerificationWorker(
            project_root=getattr(self.runtime_core, "root", "."),
            files=[file_path],
            change_id=str(preview.metadata.get("change_id", "")),
        )
        worker.signals.finished.connect(lambda r: self._verification_done(r, True))
        worker.signals.failed.connect(lambda msg: self._verification_done(msg, False))

        self._verification_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _verification_done(self, result: Any, success: bool) -> None:
        self.workspace.finding_details.set_preview_busy(False)
        self._verification_worker = None

        status_msg = "Verification passed" if success else f"Verification failed: {result}"
        self.workspace.status_label.setText(status_msg)
        self.workspace.finding_details.set_action_output(status_msg)

    @Slot(object)
    def _reject_preview(self, value: Any) -> None:
        self._current_preview = None
        self.workspace.status_label.setText("Preview rejected")

    @Slot(object)
    def _copy_patch(self, value: Any) -> None:
        preview = PreviewDiff.from_value(value if value is not None else self._current_preview)
        if preview.patch:
            QApplication.clipboard().setText(preview.patch)
            self.workspace.status_label.setText("Patch copied to clipboard")
        else:
            self.workspace.finding_details.set_action_output("No patch available to copy.")

    @Slot(dict)
    def _ignore_finding(self, finding: dict[str, Any]) -> None:
        service = ServiceResolver.get_service(self.runtime_core)
        ignore_fn = getattr(service, "ignore_finding", None)

        if callable(ignore_fn):
            try:
                ignore_fn(finding)
            except Exception as exc:
                self.workspace.finding_details.set_action_output(f"Failed to ignore: {exc}")
                return

        remaining = [
            item
            for item in self.workspace.findings.findings
            if not (
                item.get("category") == finding.get("category")
                and item.get("title") == finding.get("title")
                and item.get("file") == finding.get("file")
                and item.get("line") == finding.get("line")
            )
        ]

        self.workspace.findings.set_findings(remaining)
        self.workspace.health_card.set_findings(remaining)
        self._current_finding = None
        self._current_review = None
        self._current_plan = None
        self._current_preview = None
        self.workspace.finding_details.clear()
        self.workspace.status_label.setText("Finding ignored")

    def _process_raw_findings(self, raw_findings: list[Any]) -> list[dict[str, Any]]:
        processed = []
        for item in raw_findings:
            if hasattr(item, "to_dict") and callable(item.to_dict):
                processed.append(item.to_dict())
            elif isinstance(item, dict):
                processed.append(item)
            else:
                processed.append({
                    "title": getattr(item, "title", getattr(item, "name", str(item))),
                    "category": getattr(item, "category", getattr(item, "type", "general")),
                    "file": getattr(item, "file", getattr(item, "file_path", "")),
                    "line": getattr(item, "line", getattr(item, "line_number", 1)),
                    "description": getattr(item, "description", ""),
                })
        return processed

    @Slot()
    def refresh_cached_state(self) -> None:
        # Do not overwrite state during active scan
        if self._is_scanning:
            return

        status = ServiceResolver.get_status(self.runtime_core)
        raw_findings = status.get("findings", [])

        # Only update if the resolver actually returned findings
        if raw_findings:
            processed = self._process_raw_findings(raw_findings)
            self.workspace.findings.set_findings(processed)
            self.workspace.health_card.set_findings(processed)

    def set_runtime_core(self, runtime_core: Any) -> None:
        self.runtime_core = runtime_core
        self.workspace.update_runtime_core(runtime_core)
        self.refresh_cached_state()

    def _current_mode(self) -> str:
        mode_selector = self.workspace.mode_selector
        if hasattr(mode_selector, "current_mode"):
            val = mode_selector.current_mode
            return val() if callable(val) else str(val)
        return "manual"

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementPanel {
                background-color: #10151d;
                border: 1px solid #263241;
                border-radius: 12px;
            }
            QLabel#SelfImprovementTitle {
                color: #23B8FF; font-size: 15px; font-weight: 800;
            }
            QLabel#SelfImprovementStatus {
                color: #94a3b8; font-size: 11px; padding-left: 8px;
            }
            QPushButton {
                background-color: #1f2937; color: #ffffff;
                border: 1px solid #334155; border-radius: 6px;
                padding: 6px 14px; font-size: 11px; font-weight: 700;
            }
            QPushButton:hover { background-color: #2563eb; }
            """
        )

    def closeEvent(self, event) -> None:
        if self.timer.isActive():
            self.timer.stop()
        self.task_controller.cleanup()
        super().closeEvent(event)