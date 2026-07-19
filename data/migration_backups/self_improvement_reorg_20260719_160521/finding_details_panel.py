from __future__ import annotations

from typing import Any, Mapping, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .preview_diff_panel import PreviewDiff, PreviewDiffPanel
from .repair_plan_panel import RepairPlanPanel


class ReviewSection(QFrame):
    """Small reusable card used by scanner, review, and status sections."""

    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ReviewSection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        self.title = QLabel(title, self)
        self.title.setObjectName("ReviewSectionTitle")
        layout.addWidget(self.title)

        self.body = QLabel("—", self)
        self.body.setObjectName("ReviewSectionBody")
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.body)

    def set_text(self, text: str) -> None:
        self.body.setText(str(text).strip() or "—")


class FindingDetailsPanel(QFrame):
    """
    Progressive Self Improvement workflow panel.

    The complete visible workflow is:

        Scanner Summary
            -> AI Review
            -> Repair Plan
            -> Preview Diff

    Earlier stages remain visible while later stages are produced. The
    embedded PreviewDiffPanel is reusable and exposes safe apply, verify,
    reject, and copy signals without performing backend work itself.
    """

    review_requested = Signal(dict)
    plan_requested = Signal(dict)
    fix_requested = Signal(dict)
    ignore_requested = Signal(dict)

    apply_requested = Signal(object)
    verify_requested = Signal(object)
    reject_requested = Signal(object)
    copy_patch_requested = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._finding: dict[str, Any] = {}
        self._review: dict[str, Any] = {}
        self._plan: dict[str, Any] = {}
        self._busy_action = ""

        self.setObjectName("FindingDetailsPanel")

        self._build_ui()
        self._apply_styles()
        self.clear()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        self._build_header(root)
        self._build_metrics(root)

        self.confidence_bar = QProgressBar(self)
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setTextVisible(False)
        self.confidence_bar.setFixedHeight(5)
        root.addWidget(self.confidence_bar)

        self.workflow_scroll = QScrollArea(self)
        self.workflow_scroll.setObjectName("FindingWorkflowScroll")
        self.workflow_scroll.setWidgetResizable(True)
        self.workflow_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.workflow_content = QWidget(self.workflow_scroll)
        self.workflow_content.setObjectName("FindingWorkflowContent")

        self.workflow_layout = QVBoxLayout(self.workflow_content)
        self.workflow_layout.setContentsMargins(0, 0, 0, 0)
        self.workflow_layout.setSpacing(8)

        self._build_scanner_summary()
        self._build_review_container()
        self._build_action_output()
        self._build_repair_plan()
        self._build_preview_diff()

        self.workflow_layout.addStretch(1)

        self.workflow_scroll.setWidget(self.workflow_content)
        root.addWidget(self.workflow_scroll, 1)

        self._build_buttons(root)

    def _build_header(self, root: QVBoxLayout) -> None:
        header = QHBoxLayout()
        header.setSpacing(8)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.title_label = QLabel("Select a finding", self)
        self.title_label.setObjectName("FindingDetailsTitle")
        self.title_label.setWordWrap(True)
        title_box.addWidget(self.title_label)

        self.location_label = QLabel("No finding selected", self)
        self.location_label.setObjectName("FindingLocation")
        self.location_label.setWordWrap(True)
        title_box.addWidget(self.location_label)

        header.addLayout(title_box, 1)

        self.severity_label = QLabel("—", self)
        self.severity_label.setObjectName("SeverityBadge")
        self.severity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.severity_label.setMinimumWidth(70)
        header.addWidget(self.severity_label)

        root.addLayout(header)

    def _build_metrics(self, root: QVBoxLayout) -> None:
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(14)
        metrics.setVerticalSpacing(3)

        metrics.addWidget(self._caption("Category"), 0, 0)
        self.category_value = self._value("—")
        metrics.addWidget(self.category_value, 0, 1)

        metrics.addWidget(self._caption("Confidence"), 0, 2)
        self.confidence_value = self._value("—")
        metrics.addWidget(self.confidence_value, 0, 3)

        metrics.addWidget(self._caption("Decision"), 1, 0)
        self.decision_value = self._value("Review")
        self.decision_value.setObjectName("DecisionValue")
        metrics.addWidget(self.decision_value, 1, 1)

        metrics.addWidget(self._caption("AI status"), 1, 2)
        self.ai_status_value = self._value("Not reviewed")
        metrics.addWidget(self.ai_status_value, 1, 3)

        root.addLayout(metrics)

    def _build_scanner_summary(self) -> None:
        self.summary_container = self._workflow_container(
            "SCANNER SUMMARY"
        )
        layout = self.summary_container.layout()

        self.issue_section = ReviewSection(
            "Issue",
            self.summary_container,
        )
        self.reason_section = ReviewSection(
            "Scanner recommendation",
            self.summary_container,
        )
        layout.addWidget(self.issue_section)
        layout.addWidget(self.reason_section)

        self.workflow_layout.addWidget(self.summary_container)

    def _build_review_container(self) -> None:
        self.review_container = self._workflow_container("AI REVIEW")
        layout = self.review_container.layout()

        self.summary_section = ReviewSection(
            "AI summary",
            self.review_container,
        )
        self.evidence_section = ReviewSection(
            "Evidence",
            self.review_container,
        )
        self.impact_section = ReviewSection(
            "Impact",
            self.review_container,
        )
        self.repair_section = ReviewSection(
            "Suggested fix",
            self.review_container,
        )
        self.validation_section = ReviewSection(
            "Validation",
            self.review_container,
        )

        for section in (
            self.summary_section,
            self.evidence_section,
            self.impact_section,
            self.repair_section,
            self.validation_section,
        ):
            layout.addWidget(section)

        self.workflow_layout.addWidget(self.review_container)

    def _build_action_output(self) -> None:
        self.action_output_container = self._workflow_container(
            "ACTION STATUS"
        )
        layout = self.action_output_container.layout()

        self.action_output_section = ReviewSection(
            "Result",
            self.action_output_container,
        )
        layout.addWidget(self.action_output_section)

        self.workflow_layout.addWidget(self.action_output_container)

    def _build_repair_plan(self) -> None:
        self.repair_plan_panel = RepairPlanPanel(self.workflow_content)
        self.workflow_layout.addWidget(self.repair_plan_panel)

    def _build_preview_diff(self) -> None:
        self.preview_diff_panel = PreviewDiffPanel(self.workflow_content)

        self.preview_diff_panel.apply_requested.connect(
            self.apply_requested.emit
        )
        self.preview_diff_panel.verify_requested.connect(
            self.verify_requested.emit
        )
        self.preview_diff_panel.reject_requested.connect(
            self._on_preview_rejected
        )
        self.preview_diff_panel.copy_patch_requested.connect(
            self.copy_patch_requested.emit
        )

        self.workflow_layout.addWidget(self.preview_diff_panel)

    def _build_buttons(self, root: QVBoxLayout) -> None:
        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.review_button = QPushButton("AI Review", self)
        self.review_button.setObjectName("PrimaryButton")

        self.plan_button = QPushButton("Plan", self)
        self.plan_button.setObjectName("PlanButton")

        self.fix_button = QPushButton("Generate Preview", self)
        self.fix_button.setObjectName("PreviewButton")

        self.ignore_button = QPushButton("Ignore", self)

        self.review_button.clicked.connect(
            lambda: self.review_requested.emit(dict(self._finding))
        )
        self.plan_button.clicked.connect(
            lambda: self.plan_requested.emit(dict(self._finding))
        )
        self.fix_button.clicked.connect(
            lambda: self.fix_requested.emit(dict(self._finding))
        )
        self.ignore_button.clicked.connect(
            lambda: self.ignore_requested.emit(dict(self._finding))
        )

        buttons.addWidget(self.review_button, 1)
        buttons.addWidget(self.plan_button, 1)
        buttons.addWidget(self.fix_button, 1)
        buttons.addWidget(self.ignore_button, 1)

        root.addLayout(buttons)

    def _workflow_container(self, heading: str) -> QFrame:
        container = QFrame(self.workflow_content)
        container.setObjectName("WorkflowContainer")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        label = QLabel(heading, container)
        label.setObjectName("WorkflowHeading")
        layout.addWidget(label)

        return container

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("FindingDetailsCaption")
        return label

    def _value(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("FindingDetailsValue")
        label.setWordWrap(True)
        return label

    def set_finding(self, finding: Mapping[str, Any]) -> None:
        self._finding = dict(finding)
        self._review = {}
        self._plan = {}

        title = str(
            self._finding.get(
                "title",
                self._finding.get("description", "Finding"),
            )
        )
        severity = str(
            self._finding.get("severity", "info")
        ).upper()
        category = str(
            self._finding.get("category", "—")
        ).title()

        file_name = str(
            self._finding.get("file", "") or "No file"
        )
        line = self._finding.get("line", 0)

        location = file_name
        if line:
            location = f"{file_name}:{line}"

        confidence = self._confidence_percent(
            self._finding.get("confidence", 0)
        )
        description = str(
            self._finding.get("description", "")
        ).strip()
        suggested = str(
            self._finding.get("suggested_request", "")
        ).strip()

        self.title_label.setText(title)
        self.location_label.setText(location)
        self._set_severity(severity)

        self.category_value.setText(category)
        self.confidence_value.setText(f"{confidence}%")
        self.confidence_bar.setValue(confidence)
        self.decision_value.setText(
            self._scanner_decision(severity)
        )
        self.ai_status_value.setText("Not reviewed")

        self.issue_section.set_text(
            description or "The scanner reported a project finding."
        )
        self.reason_section.set_text(
            suggested or "Review the finding before making changes."
        )

        self.clear_review()
        self.clear_plan()
        self.clear_preview()
        self.clear_action_output()

        self.review_container.hide()
        self.repair_plan_panel.hide()
        self.preview_diff_panel.hide()
        self.action_output_container.hide()

        self._set_buttons_enabled(True)

    def show_review(self, result: Mapping[str, Any]) -> None:
        review = dict(result or {})
        self._review = review

        self.summary_section.set_text(
            str(review.get("summary", ""))
        )
        self.evidence_section.set_text(
            self._stringify(review.get("evidence", ""))
        )
        self.impact_section.set_text(
            self._stringify(review.get("impact", ""))
        )
        self.repair_section.set_text(
            self._stringify(
                review.get("recommended_repair")
                or review.get("repair")
                or review.get("suggested_fix")
                or ""
            )
        )
        self.validation_section.set_text(
            self._stringify(review.get("validation", ""))
        )

        risk = str(review.get("risk", "")).upper().strip()
        decision = str(
            review.get("decision", "")
        ).upper().strip()

        if risk:
            self._set_severity(risk)
        if decision:
            self.decision_value.setText(decision)

        provider = str(review.get("provider", "AI"))
        model = str(review.get("model", ""))
        status = provider
        if model:
            status += f" · {model}"

        self.ai_status_value.setText(status)
        self.review_container.show()
        self.action_output_container.hide()

        self.set_busy(False)
        self._scroll_to_widget(self.review_container)

    def show_plan(self, plan: Mapping[str, Any]) -> None:
        payload = dict(plan or {})
        self._plan = payload

        self.repair_plan_panel.show_plan(payload)
        self.repair_plan_panel.show()
        self.action_output_container.hide()

        decision = str(
            payload.get("decision", "")
        ).upper().strip()
        if decision:
            self.decision_value.setText(decision)

        self.set_busy(False)
        self._scroll_to_widget(self.repair_plan_panel)

    def show_diff(self, value: Any) -> None:
        """
        Show a generated patch as the fourth workflow stage.

        Accepts PreviewDiff, a mapping, an object exposing to_dict(), or a
        raw unified-diff string.
        """
        self.preview_diff_panel.show_diff(value)
        self.preview_diff_panel.show()
        self.action_output_container.hide()

        self.set_busy(False)
        self._scroll_to_widget(self.preview_diff_panel)

    def show_preview(self, value: Any) -> None:
        """Alias retained for controller code that uses show_preview()."""
        self.show_diff(value)

    def set_preview_busy(
        self,
        busy: bool,
        message: str = "Generating preview...",
    ) -> None:
        self.preview_diff_panel.show()
        self.preview_diff_panel.set_busy(busy, message)

        if busy:
            self._busy_action = "preview"
            self._set_workflow_buttons_busy(True)
            self.ai_status_value.setText(message)
            self._scroll_to_widget(self.preview_diff_panel)
        else:
            self._busy_action = ""
            self._set_workflow_buttons_busy(False)

    def set_preview_validation(
        self,
        state: str,
        message: str = "",
    ) -> None:
        self.preview_diff_panel.set_validation(state, message)

    def set_action_output(self, text: str) -> None:
        """
        Compatibility output for fix, ignore, error, and legacy handlers.
        """
        self.action_output_section.set_text(text)
        self.action_output_container.show()
        self.set_busy(False)
        self._scroll_to_widget(self.action_output_container)

    def set_busy(
        self,
        busy: bool,
        message: str = "",
    ) -> None:
        has_finding = bool(self._finding)

        if busy:
            lower_message = message.lower()
            if "preview" in lower_message or "diff" in lower_message:
                self._busy_action = "preview"
            elif "plan" in lower_message:
                self._busy_action = "plan"
            else:
                self._busy_action = "review"

            self._set_workflow_buttons_busy(True)

            if self._busy_action == "plan":
                self.plan_button.setText("Planning...")
                self.repair_plan_panel.set_busy(
                    True,
                    message or "Planning repair strategy...",
                )
                self.repair_plan_panel.show()
                self._scroll_to_widget(self.repair_plan_panel)

            elif self._busy_action == "preview":
                self.fix_button.setText("Generating...")
                self.preview_diff_panel.set_busy(
                    True,
                    message or "Generating preview...",
                )
                self.preview_diff_panel.show()
                self._scroll_to_widget(self.preview_diff_panel)

            else:
                self.review_button.setText("Reviewing...")

            self.ai_status_value.setText(
                message or "Analysing in background..."
            )
            return

        if self._busy_action == "plan":
            self.repair_plan_panel.set_busy(False)
        elif self._busy_action == "preview":
            self.preview_diff_panel.set_busy(False)

        self._busy_action = ""

        self.review_button.setText("AI Review")
        self.plan_button.setText("Plan")
        self.fix_button.setText("Generate Preview")

        self.review_button.setEnabled(has_finding)
        self.plan_button.setEnabled(has_finding)
        self.fix_button.setEnabled(has_finding)
        self.ignore_button.setEnabled(has_finding)

    def clear_review(self) -> None:
        self._review = {}
        for section in (
            self.summary_section,
            self.evidence_section,
            self.impact_section,
            self.repair_section,
            self.validation_section,
        ):
            section.set_text("—")

    def clear_plan(self) -> None:
        self._plan = {}
        self.repair_plan_panel.clear()
        self.repair_plan_panel.hide()

    def clear_preview(self) -> None:
        self.preview_diff_panel.clear()
        self.preview_diff_panel.hide()

    def clear_action_output(self) -> None:
        self.action_output_section.set_text("—")
        self.action_output_container.hide()

    def clear(self) -> None:
        self._finding = {}
        self._review = {}
        self._plan = {}
        self._busy_action = ""

        self.title_label.setText("Select a finding")
        self.location_label.setText("No finding selected")
        self._set_severity("")

        self.category_value.setText("—")
        self.confidence_value.setText("—")
        self.decision_value.setText("—")
        self.ai_status_value.setText("Not reviewed")
        self.confidence_bar.setValue(0)

        self.issue_section.set_text(
            "Select a finding from the table."
        )
        self.reason_section.set_text("—")

        self.clear_review()
        self.clear_plan()
        self.clear_preview()
        self.clear_action_output()

        self.review_container.hide()
        self._set_buttons_enabled(False)

    def _on_preview_rejected(self, preview: PreviewDiff) -> None:
        self.reject_requested.emit(preview)
        self.clear_preview()
        self.set_action_output(
            "Generated patch rejected. No project files were changed."
        )

    def _set_severity(self, severity: str) -> None:
        value = str(severity or "—").upper()
        property_value = value.lower() if value != "—" else ""

        self.severity_label.setText(value)
        self.severity_label.setProperty(
            "severity",
            property_value,
        )
        self.severity_label.style().unpolish(
            self.severity_label
        )
        self.severity_label.style().polish(
            self.severity_label
        )

    def _set_buttons_enabled(self, enabled: bool) -> None:
        self.review_button.setEnabled(enabled)
        self.plan_button.setEnabled(enabled)
        self.fix_button.setEnabled(enabled)
        self.ignore_button.setEnabled(enabled)

    def _set_workflow_buttons_busy(self, busy: bool) -> None:
        enabled = not busy and bool(self._finding)
        self.review_button.setEnabled(enabled)
        self.plan_button.setEnabled(enabled)
        self.fix_button.setEnabled(enabled)
        self.ignore_button.setEnabled(enabled)

    def _scroll_to_widget(self, widget: QWidget) -> None:
        self.workflow_scroll.ensureWidgetVisible(widget, 0, 12)

    @staticmethod
    def _confidence_percent(value: Any) -> int:
        try:
            number = float(value)
            if number <= 1:
                number *= 100
            return max(0, min(100, round(number)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _scanner_decision(severity: str) -> str:
        return {
            "CRITICAL": "FIX NOW",
            "HIGH": "FIX NOW",
            "MEDIUM": "PLAN FIRST",
            "LOW": "MONITOR",
            "INFO": "MONITOR",
        }.get(severity, "REVIEW")

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            return "\n".join(
                f"{key}: {item}"
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple, set)):
            return "\n".join(f"• {item}" for item in value)
        return str(value or "")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#FindingDetailsPanel {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QLabel#FindingDetailsTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: 800;
            }

            QLabel#FindingLocation {
                color: #7f8b99;
                font-size: 9px;
            }

            QLabel#SeverityBadge {
                color: #f8fafc;
                background-color: #334155;
                border: 1px solid #475569;
                border-radius: 7px;
                padding: 5px 9px;
                font-size: 10px;
                font-weight: 800;
            }

            QLabel#SeverityBadge[severity="low"],
            QLabel#SeverityBadge[severity="info"] {
                color: #fbbf24;
                background-color: #3b2f12;
                border-color: #6b5318;
            }

            QLabel#SeverityBadge[severity="medium"] {
                color: #fb923c;
                background-color: #3c2415;
                border-color: #7c3f17;
            }

            QLabel#SeverityBadge[severity="high"],
            QLabel#SeverityBadge[severity="critical"] {
                color: #f87171;
                background-color: #3d171b;
                border-color: #7f1d1d;
            }

            QLabel#FindingDetailsCaption {
                color: #718096;
                font-size: 9px;
                font-weight: 700;
            }

            QLabel#FindingDetailsValue,
            QLabel#DecisionValue {
                color: #dbe3eb;
                font-size: 10px;
            }

            QLabel#DecisionValue {
                color: #60a5fa;
                font-weight: 800;
            }

            QLabel#WorkflowHeading {
                color: #23b8ff;
                font-size: 10px;
                font-weight: 900;
                padding-top: 2px;
            }

            QProgressBar {
                border: none;
                background-color: #263241;
                border-radius: 2px;
            }

            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 2px;
            }

            QFrame#ReviewSection {
                background-color: #111827;
                border: 1px solid #293548;
                border-radius: 7px;
            }

            QLabel#ReviewSectionTitle {
                color: #7dd3fc;
                font-size: 9px;
                font-weight: 800;
            }

            QLabel#ReviewSectionBody {
                color: #dbe3eb;
                font-size: 10px;
            }

            QScrollArea#FindingWorkflowScroll {
                background: transparent;
                border: none;
            }

            QWidget#FindingWorkflowContent,
            QScrollArea#FindingWorkflowScroll > QWidget > QWidget {
                background: transparent;
            }

            QPushButton {
                background-color: #1f2937;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 9px;
                font-size: 10px;
                font-weight: 700;
            }

            QPushButton#PrimaryButton {
                background-color: #1d4ed8;
                border-color: #3b82f6;
            }

            QPushButton#PlanButton {
                background-color: #164e63;
                border-color: #0891b2;
            }

            QPushButton#PreviewButton {
                background-color: #4c1d95;
                border-color: #7c3aed;
            }

            QPushButton:hover {
                background-color: #2563eb;
            }

            QPushButton:disabled {
                color: #64748b;
                background-color: #18202b;
                border-color: #263241;
            }
            """
        )


__all__ = [
    "ReviewSection",
    "FindingDetailsPanel",
]
