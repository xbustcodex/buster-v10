"""
Buster Integration Hub Panel - Production Safe Ingestion Workspace.

Responsibilities
----------------
- Ingest dropped source files and patches.
- Detect the most likely destination through repository knowledge.
- Run structural analysis, safety policy checks and AI review off the UI thread.
- Preview and simulate the transaction before any write occurs.
- Apply changes through the existing PatchTransaction lifecycle.
- Publish integration lifecycle events into the active Buster runtime.
- Preserve learned routing and repository reindexing.
"""

from __future__ import annotations

import ast
import html
import logging
import os
import py_compile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from buster.core.integration.ai_patch_reviewer import AIPatchReviewer
from buster.core.integration.hub_lifecycle import HubState, SafetyValidator
from buster.core.integration.patch_analyzer import PatchAnalyzer
from buster.core.integration.repo_knowledge_base import RepoKnowledgeBase
from buster.runtime.audit_service import AuditService
from buster.ui.v9.panels.self_improvement.apply.patch_transaction import (
    PatchTransaction,
)

logger = logging.getLogger(__name__)

MAX_INGEST_BYTES = 2 * 1024 * 1024
PROTECTED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "backups",
    "backup",
}
HIGH_RISK_PREFIXES = (
    "buster/kernel/",
    "buster/runtime/",
    "buster/security/",
    "buster/core/",
)


@dataclass(slots=True)
class AnalysisResult:
    """Complete immutable result returned by the background analyzer."""

    file_path: str
    content: str
    match_info: dict[str, Any]
    diff_info: dict[str, Any]
    delta: dict[str, Any]
    components: list[str]
    ai_review: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    policy_passed: bool


class IntegrationAnalysisWorker(QObject):
    """Runs ingestion analysis outside the Qt GUI thread."""

    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(
        self,
        file_path: str,
        project_root: Path,
        knowledge_base: RepoKnowledgeBase,
        analyzer: PatchAnalyzer,
    ):
        super().__init__()
        self.file_path = file_path
        self.project_root = project_root
        self.kb = knowledge_base
        self.analyzer = analyzer

    @Slot()
    def run(self) -> None:
        try:
            path = Path(self.file_path).resolve()
            self.progress.emit("Reading source file")
            content = self._read_source(path)

            self.progress.emit("Validating Python syntax")
            self._validate_python_if_needed(path, content)

            self.progress.emit("Detecting target route")
            match_info = self.kb.match_dropped_content(str(path)) or {}
            target_rel = str(match_info.get("target_rel_path") or "").strip()
            if not target_rel:
                raise ValueError(
                    "Repository knowledge base did not return a target path."
                )

            confidence = self._normalise_confidence(
                match_info.get("confidence", 0)
            )
            match_info["confidence"] = confidence
            match_info.setdefault("category", "Unknown")

            target_path = self._safe_target_path(target_rel)

            self.progress.emit("Computing unified diff")
            diff_info = (
                self.kb.compute_diff_summary(content, target_rel) or {}
            )

            self.progress.emit("Running structural analysis")
            delta = (
                self.analyzer.analyze_structural_delta(
                    target_rel,
                    content,
                )
                or {}
            )
            components = list(
                self.analyzer.map_affected_components(
                    target_rel,
                    content,
                )
                or []
            )

            self.progress.emit("Running AI patch review")
            ai_review = (
                AIPatchReviewer.review_patch(
                    path.name,
                    content,
                    target_rel,
                )
                or {}
            )

            self.progress.emit("Evaluating safety policy")
            passed, warnings, errors = SafetyValidator.evaluate_safety(
                self.project_root,
                target_rel,
                content,
                confidence,
            )

            warnings = list(warnings or [])
            errors = list(errors or [])

            if self._is_high_risk(target_rel):
                warnings.append(
                    "High-risk target: runtime/kernel/core/security change."
                )

            if target_path.exists() and not target_path.is_file():
                errors.append("Detected target exists but is not a file.")

            passed = bool(passed) and not errors

            self.completed.emit(
                AnalysisResult(
                    file_path=str(path),
                    content=content,
                    match_info=match_info,
                    diff_info=diff_info,
                    delta=delta,
                    components=components,
                    ai_review=ai_review,
                    warnings=warnings,
                    errors=errors,
                    policy_passed=passed,
                )
            )
        except Exception as exc:
            logger.exception("Integration Hub analysis failed")
            self.failed.emit(str(exc))

    def _read_source(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Source file does not exist: {path}")

        size = path.stat().st_size
        if size > MAX_INGEST_BYTES:
            raise ValueError(
                f"File is too large ({size:,} bytes). "
                f"Maximum allowed size is {MAX_INGEST_BYTES:,} bytes."
            )

        raw = path.read_bytes()
        if b"\x00" in raw:
            raise ValueError("Binary files cannot be ingested.")

        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "File must be UTF-8 encoded."
            ) from exc

    @staticmethod
    def _validate_python_if_needed(path: Path, content: str) -> None:
        if path.suffix.lower() != ".py":
            return

        ast.parse(content, filename=str(path))

        with tempfile.TemporaryDirectory(
            prefix="buster_hub_validate_"
        ) as temp_dir:
            temp_path = Path(temp_dir) / path.name
            temp_path.write_text(content, encoding="utf-8")
            py_compile.compile(str(temp_path), doraise=True)

    def _safe_target_path(self, target_rel: str) -> Path:
        rel = Path(target_rel.replace("\\", "/"))
        if rel.is_absolute():
            raise ValueError("Target path must be relative to the project.")

        if any(part in PROTECTED_PARTS for part in rel.parts):
            raise ValueError(
                f"Target path contains a protected directory: {target_rel}"
            )

        root = self.project_root.resolve()
        target = (root / rel).resolve()

        if target != root and root not in target.parents:
            raise ValueError("Detected target escapes the project root.")

        return target

    @staticmethod
    def _normalise_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0

        if 0.0 <= confidence <= 1.0:
            confidence *= 100.0

        return max(0.0, min(100.0, confidence))

    @staticmethod
    def _is_high_risk(target_rel: str) -> bool:
        normalised = target_rel.replace("\\", "/").lower()
        return normalised.startswith(HIGH_RISK_PREFIXES)


class IntegrationHubPanel(QWidget):
    """Controlled ingestion, preview and transactional deployment workspace."""

    ingestion_completed = Signal(str, str)
    transaction_committed = Signal(str, str)
    transaction_failed = Signal(str)

    def __init__(self, runtime_core=None, live=None, parent=None):
        super().__init__(parent)
        self.runtime_core = runtime_core
        self.live = live
        self.project_root = self._resolve_project_root()

        self.kb = RepoKnowledgeBase(self.project_root)
        self.analyzer = PatchAnalyzer(
            self.project_root,
            getattr(self.kb, "index", {}),
        )
        self.audit_service = self._resolve_audit_service()

        self.current_state = HubState.IDLE
        self._active_file_path: Optional[str] = None
        self._match_info: dict[str, Any] = {}
        self._file_content = ""
        self._diff_info: dict[str, Any] = {}
        self._delta: dict[str, Any] = {}
        self._components: list[str] = []
        self._ai_review: dict[str, Any] = {}
        self._safety_warnings: list[str] = []
        self._safety_errors: list[str] = []
        self._policy_passed = False

        self._analysis_thread: Optional[QThread] = None
        self._analysis_worker: Optional[IntegrationAnalysisWorker] = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Runtime resolution
    # ------------------------------------------------------------------

    def _resolve_project_root(self) -> Path:
        candidates: list[Any] = []

        if self.runtime_core is not None:
            for name in (
                "project_root",
                "workspace_root",
                "repo_root",
                "root_path",
            ):
                candidates.append(getattr(self.runtime_core, name, None))

            workspace = getattr(self.runtime_core, "workspace", None)
            if workspace is not None:
                for name in ("root", "path", "project_root"):
                    candidates.append(getattr(workspace, name, None))

        if self.live is not None:
            for name in ("project_root", "workspace_root"):
                candidates.append(getattr(self.live, name, None))

        candidates.append(Path.cwd())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                path = Path(candidate).expanduser().resolve()
            except (TypeError, OSError):
                continue
            if path.exists():
                return path

        return Path.cwd().resolve()

    def _resolve_audit_service(self) -> AuditService:
        if self.runtime_core is not None:
            service = getattr(
                self.runtime_core,
                "audit_service",
                None,
            )
            if service is not None:
                return service

            services = getattr(self.runtime_core, "services", None)
            if services is not None:
                service = self._resolve_named_service(
                    services,
                    "audit_service",
                )
                if service is not None:
                    return service

        return AuditService()

    @staticmethod
    def _resolve_named_service(container: Any, name: str) -> Any:
        if isinstance(container, dict):
            return container.get(name)

        for method_name in ("get", "resolve", "service"):
            method = getattr(container, method_name, None)
            if callable(method):
                try:
                    value = method(name)
                    if value is not None:
                        return value
                except Exception:
                    continue

        return getattr(container, name, None)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setObjectName("IntegrationHubPanel")
        self.setStyleSheet(
            """
            QWidget#IntegrationHubPanel {
                background:#0B1726;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }
            QPushButton {
                background:#17334E;
                color:#E8F2FC;
                border:1px solid #2B587B;
                border-radius:6px;
                padding:6px 11px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#204B70;
                border-color:#23B8FF;
            }
            QPushButton:disabled {
                background:#142536;
                color:#60758A;
                border-color:#24394C;
            }
            QLineEdit, QTextEdit {
                background:#081522;
                color:#DCEBFF;
                border:1px solid #244560;
                border-radius:6px;
                selection-background-color:#20527A;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("BUSTER INTEGRATION HUB")
        title.setStyleSheet(
            "color:#23B8FF;font-size:21px;font-weight:900;"
            "letter-spacing:1px;background:transparent;"
        )
        subtitle = QLabel(
            "Controlled ingestion · repository intelligence · "
            "transactional verification · rollback protection"
        )
        subtitle.setStyleSheet(
            "color:#9EB6CF;font-size:11px;background:transparent;"
        )
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.lifecycle_ribbon = QLabel("State: IDLE")
        self.lifecycle_ribbon.setStyleSheet(
            "background:#081522;color:#9EB6CF;border:1px solid #244560;"
            "border-radius:6px;padding:7px 11px;font-family:Consolas;"
            "font-weight:700;font-size:11px;"
        )
        layout.addWidget(self.lifecycle_ribbon)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(9)

        self.drop_card = QFrame()
        self.drop_card.setObjectName("DropCard")
        self.drop_card.setAcceptDrops(True)
        self.drop_card.setCursor(Qt.PointingHandCursor)
        self.drop_card.setMinimumHeight(135)
        self.drop_card.setStyleSheet(
            """
            QFrame#DropCard {
                background:#081522;
                border:2px dashed #2878B8;
                border-radius:10px;
                padding:18px;
            }
            QFrame#DropCard:hover {
                border-color:#23B8FF;
                background:#10253A;
            }
            """
        )
        self.drop_card.dragEnterEvent = self._drag_enter
        self.drop_card.dropEvent = self._drop_event
        self.drop_card.mousePressEvent = self._click_browse

        drop_box = QVBoxLayout(self.drop_card)
        drop_box.setAlignment(Qt.AlignCenter)

        icon = QLabel("📦")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:32px;background:transparent;")

        text = QLabel(
            "Drop a file or patch here\nor click to browse"
        )
        text.setAlignment(Qt.AlignCenter)
        text.setStyleSheet(
            "color:#DCEBFF;font-weight:800;font-size:12px;"
            "background:transparent;"
        )

        hint = QLabel(
            "Read-only analysis occurs before transaction approval"
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            "color:#7F9AB4;font-size:10px;background:transparent;"
        )

        drop_box.addWidget(icon)
        drop_box.addWidget(text)
        drop_box.addWidget(hint)
        left_layout.addWidget(self.drop_card)

        route_row = QHBoxLayout()
        route_label = QLabel("Target:")
        route_label.setStyleSheet(
            "color:#9EB6CF;font-weight:700;background:transparent;"
        )
        route_row.addWidget(route_label)

        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText(
            "Detected route appears here"
        )
        self.target_edit.textChanged.connect(
            self._on_target_edited
        )
        route_row.addWidget(self.target_edit, 1)

        self.reset_route_btn = QPushButton("Reset")
        self.reset_route_btn.setEnabled(False)
        self.reset_route_btn.clicked.connect(
            self._reset_detected_route
        )
        route_row.addWidget(self.reset_route_btn)
        left_layout.addLayout(route_row)

        self.status_card = QFrame()
        self.status_card.setStyleSheet(
            "background:#0E1D2E;border:1px solid #244560;"
            "border-radius:8px;padding:10px;"
        )
        status_box = QVBoxLayout(self.status_card)

        self.status_text = QLabel("Awaiting file ingestion...")
        self.status_text.setWordWrap(True)
        self.status_text.setTextFormat(Qt.RichText)
        self.status_text.setStyleSheet(
            "color:#C7D8EA;font-size:11px;"
            "font-family:Consolas;background:transparent;"
        )
        status_box.addWidget(self.status_text)
        left_layout.addWidget(self.status_card, 1)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        preview_label = QLabel("PATCH INSPECTION & DIFF PREVIEW")
        preview_label.setStyleSheet(
            "color:#9EB6CF;font-size:10px;font-weight:800;"
            "background:transparent;"
        )
        right_layout.addWidget(preview_label)

        self.diff_preview = QTextEdit()
        self.diff_preview.setReadOnly(True)
        self.diff_preview.setStyleSheet(
            "QTextEdit {background:#081522;color:#BFD1E7;"
            "border:1px solid #244560;border-radius:6px;padding:8px;"
            "font-family:Consolas;font-size:11px;}"
        )
        right_layout.addWidget(self.diff_preview)

        splitter.addWidget(right_widget)
        splitter.setSizes([470, 550])
        layout.addWidget(splitter, 1)

        action_bar = QHBoxLayout()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._reset_ingestion)
        action_bar.addWidget(self.clear_btn)

        self.open_target_btn = QPushButton("Open Target Folder")
        self.open_target_btn.setEnabled(False)
        self.open_target_btn.clicked.connect(
            self._open_target_folder
        )
        action_bar.addWidget(self.open_target_btn)

        action_bar.addStretch()

        self.learn_btn = QPushButton("Remember Route")
        self.learn_btn.setEnabled(False)
        self.learn_btn.clicked.connect(self._learn_route)
        action_bar.addWidget(self.learn_btn)

        self.simulate_btn = QPushButton("Simulate Transaction")
        self.simulate_btn.setEnabled(False)
        self.simulate_btn.clicked.connect(self._run_simulation)
        action_bar.addWidget(self.simulate_btn)

        self.apply_btn = QPushButton("Apply Patch Transaction")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(
            self._execute_transaction_flow
        )
        action_bar.addWidget(self.apply_btn)

        layout.addLayout(action_bar)

    # ------------------------------------------------------------------
    # State and events
    # ------------------------------------------------------------------

    def _set_state(
        self,
        state: HubState,
        detail: str = "",
    ) -> None:
        self.current_state = state
        text = f"State: {state.name}"
        if detail:
            text += f" — {detail}"
        self.lifecycle_ribbon.setText(text)

    def _publish_event(
        self,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        if self.runtime_core is None:
            return

        payload = payload or {}

        candidates = [
            getattr(self.runtime_core, name, None)
            for name in (
                "event_bus",
                "event_router",
                "dispatcher",
                "router",
            )
        ]

        kernel = getattr(self.runtime_core, "kernel", None)
        if kernel is not None:
            candidates.extend(
                getattr(kernel, name, None)
                for name in (
                    "event_bus",
                    "event_router",
                    "dispatcher",
                    "router",
                )
            )

        for owner in candidates:
            if owner is None:
                continue

            for method_name in ("publish", "emit", "dispatch"):
                method = getattr(owner, method_name, None)
                if not callable(method):
                    continue

                for args in (
                    (event_type, payload),
                    ({"type": event_type, "payload": payload},),
                ):
                    try:
                        method(*args)
                        return
                    except TypeError:
                        continue
                    except Exception:
                        logger.exception(
                            "Integration Hub event publish failed"
                        )
                        return

    def _transaction_event_emitter(self) -> Optional[Callable[..., Any]]:
        if self.runtime_core is None:
            return None

        candidates = [
            getattr(self.runtime_core, name, None)
            for name in (
                "event_bus",
                "event_router",
                "dispatcher",
                "router",
            )
        ]

        for owner in candidates:
            if owner is None:
                continue
            for method_name in ("emit", "publish", "dispatch"):
                method = getattr(owner, method_name, None)
                if callable(method):
                    return method

        return None

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def _drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self._process_ingestion(path)
        event.acceptProposedAction()

    def _click_browse(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Integration File",
            "",
            "Python Files (*.py);;Text Files (*.txt *.json *.md);;"
            "All Files (*)",
        )
        if path:
            self._process_ingestion(path)

    def _process_ingestion(self, file_path: str) -> None:
        if self._analysis_thread is not None:
            QMessageBox.information(
                self,
                "Analysis Running",
                "Wait for the current analysis to finish.",
            )
            return

        self._reset_ingestion(keep_state=True)
        self._active_file_path = str(Path(file_path).resolve())
        self._set_state(HubState.DROPPED, Path(file_path).name)
        self._set_busy(True)
        self._publish_event(
            "integration.ingestion.started",
            {"file_path": self._active_file_path},
        )

        thread = QThread(self)
        worker = IntegrationAnalysisWorker(
            self._active_file_path,
            self.project_root,
            self.kb,
            self.analyzer,
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_analysis_progress)
        worker.completed.connect(self._on_analysis_completed)
        worker.failed.connect(self._on_analysis_failed)

        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._analysis_finished)

        self._analysis_thread = thread
        self._analysis_worker = worker
        thread.start()

    @Slot(str)
    def _on_analysis_progress(self, detail: str) -> None:
        self._set_state(HubState.ANALYZING, detail)

    @Slot(object)
    def _on_analysis_completed(self, result: AnalysisResult) -> None:
        self._file_content = result.content
        self._match_info = dict(result.match_info)
        self._diff_info = dict(result.diff_info)
        self._delta = dict(result.delta)
        self._components = list(result.components)
        self._ai_review = dict(result.ai_review)
        self._safety_warnings = list(result.warnings)
        self._safety_errors = list(result.errors)
        self._policy_passed = bool(result.policy_passed)

        target_rel = str(self._match_info["target_rel_path"])
        self.target_edit.blockSignals(True)
        self.target_edit.setText(target_rel)
        self.target_edit.blockSignals(False)
        self.reset_route_btn.setEnabled(True)

        self._set_state(
            HubState.TARGET_DETECTED,
            target_rel,
        )

        unified_diff = str(
            self._diff_info.get("unified_diff") or ""
        )
        self.diff_preview.setPlainText(
            unified_diff or self._file_content[:12000]
        )

        self._render_rich_inspection_panel()

        if self._policy_passed:
            self._set_state(
                HubState.POLICY_APPROVED,
                "Awaiting user transaction approval",
            )
        else:
            error_detail = (
                self._safety_errors[0]
                if self._safety_errors
                else "Safety policy rejected the change"
            )
            self._set_state(
                HubState.FAILED_ROLLED_BACK,
                error_detail,
            )

        self.learn_btn.setEnabled(True)
        self.simulate_btn.setEnabled(True)
        self.apply_btn.setEnabled(self._policy_passed)
        self.open_target_btn.setEnabled(True)

        self._publish_event(
            "integration.analysis.completed",
            {
                "file_path": result.file_path,
                "target_rel_path": target_rel,
                "confidence": self._match_info.get("confidence"),
                "policy_passed": self._policy_passed,
                "warnings": self._safety_warnings,
                "errors": self._safety_errors,
            },
        )
        self.ingestion_completed.emit(
            result.file_path,
            target_rel,
        )

    @Slot(str)
    def _on_analysis_failed(self, message: str) -> None:
        self._policy_passed = False
        self.status_text.setText(
            "<b style='color:#FF6961'>Analysis failed</b><br>"
            f"{html.escape(message)}"
        )
        self.diff_preview.clear()
        self._set_state(
            HubState.FAILED_ROLLED_BACK,
            message,
        )
        self._publish_event(
            "integration.failed",
            {
                "stage": "analysis",
                "file_path": self._active_file_path,
                "error": message,
            },
        )

    @Slot()
    def _analysis_finished(self) -> None:
        self._analysis_thread = None
        self._analysis_worker = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.drop_card.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.target_edit.setEnabled(not busy)
        self.learn_btn.setEnabled(
            not busy and bool(self._match_info)
        )
        self.simulate_btn.setEnabled(
            not busy and bool(self._match_info)
        )
        self.apply_btn.setEnabled(
            not busy and self._policy_passed
        )

    # ------------------------------------------------------------------
    # Route editing and rendering
    # ------------------------------------------------------------------

    def _on_target_edited(self, value: str) -> None:
        if not self._match_info:
            return

        value = value.strip()
        if not value:
            self.apply_btn.setEnabled(False)
            return

        try:
            self._validate_target_rel(value)
        except ValueError as exc:
            self.apply_btn.setEnabled(False)
            self.lifecycle_ribbon.setText(
                f"State: ROUTE INVALID — {exc}"
            )
            return

        self._match_info["target_rel_path"] = value
        self._policy_passed = False
        self.apply_btn.setEnabled(False)
        self.simulate_btn.setEnabled(False)
        self.lifecycle_ribbon.setText(
            "State: ROUTE CHANGED — rerun analysis"
        )

    def _reset_detected_route(self) -> None:
        if not self._active_file_path:
            return
        self._process_ingestion(self._active_file_path)

    def _validate_target_rel(self, target_rel: str) -> Path:
        rel = Path(target_rel.replace("\\", "/"))
        if rel.is_absolute():
            raise ValueError("Target must be relative.")

        if any(part in PROTECTED_PARTS for part in rel.parts):
            raise ValueError("Target uses a protected directory.")

        root = self.project_root.resolve()
        target = (root / rel).resolve()
        if target != root and root not in target.parents:
            raise ValueError("Target escapes project root.")

        return target

    def _render_rich_inspection_panel(self) -> None:
        file_name = html.escape(
            Path(self._active_file_path or "").name
        )
        target_rel = html.escape(
            str(self._match_info.get("target_rel_path", ""))
        )
        category = html.escape(
            str(self._match_info.get("category", "Unknown"))
        )
        confidence = html.escape(
            str(self._match_info.get("confidence", 0))
        )

        delta = self._delta
        ai_review = self._ai_review

        risk = str(ai_review.get("risk_level", "Unknown"))
        risk_class = (
            "green"
            if risk.upper() == "LOW"
            else "yellow"
            if risk.upper() in {"MEDIUM", "MODERATE"}
            else "red"
        )

        imports = ", ".join(
            html.escape(str(item))
            for item in delta.get("new_imports", [])
        ) or "None"

        components = " → ".join(
            html.escape(str(item))
            for item in self._components
        ) or "None detected"

        issues = ai_review.get("potential_issues", []) or []
        issue_html = "<br>".join(
            f"• {html.escape(str(issue))}"
            for issue in issues
        ) or "None reported"

        warnings_html = "<br>".join(
            f"• {html.escape(str(item))}"
            for item in self._safety_warnings
        ) or "None"

        errors_html = "<br>".join(
            f"• {html.escape(str(item))}"
            for item in self._safety_errors
        ) or "None"

        summary = html.escape(
            str(ai_review.get("summary", "No summary supplied."))
        )
        compatibility = html.escape(
            str(ai_review.get("compatibility", "Unknown"))
        )

        self.status_text.setText(
            f"""
            <style>
                .header {{color:#23B8FF;font-weight:800;font-size:13px;}}
                .dim {{color:#8FA9C4;}}
                .value {{color:#EAF2FF;font-weight:600;}}
                .green {{color:#31D158;}}
                .yellow {{color:#FFB000;}}
                .red {{color:#FF6961;}}
                .graph {{color:#23B8FF;font-family:Consolas;}}
            </style>

            <div class="header">{file_name}</div>
            <hr color="#244560">

            <span class="dim">Detected type:</span>
            <span class="value">{category}</span><br>
            <span class="dim">Confidence:</span>
            <span class="green">{confidence}%</span><br>
            <span class="dim">Destination:</span>
            <code>{target_rel}</code><br>
            <span class="dim">Existing file:</span>
            <span class="value">
            {'Yes' if delta.get('is_existing') else 'No — new file'}
            </span>

            <div class="header">Change summary</div>
            <span class="green">+ {delta.get('added_classes', 0)}
            classes</span><br>
            <span class="green">+ {delta.get('added_funcs', 0)}
            functions</span><br>
            <span class="dim">~ {delta.get('modified_funcs', 0)}
            functions modified</span><br>
            <span class="red">- {delta.get('removed_funcs', 0)}
            functions removed</span>

            <div class="header">New imports</div>
            <span class="value">{imports}</span>

            <div class="header">Affected components</div>
            <span class="graph">{components}</span>

            <div class="header">AI patch review</div>
            <span class="dim">Summary:</span>
            <span class="value">{summary}</span><br>
            <span class="dim">Risk:</span>
            <span class="{risk_class}">{html.escape(risk)}</span><br>
            <span class="dim">Compatibility:</span>
            <span class="green">{compatibility}</span><br>
            <span class="dim">Potential issues:</span><br>
            {issue_html}

            <div class="header">Safety warnings</div>
            <span class="yellow">{warnings_html}</span>

            <div class="header">Blocking errors</div>
            <span class="red">{errors_html}</span>
            """
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _run_simulation(self) -> None:
        if not self._match_info or not self._file_content:
            return

        target_rel = str(
            self._match_info.get("target_rel_path") or ""
        )

        try:
            self._validate_target_rel(target_rel)
            simulation = (
                self.analyzer.simulate_patch_transaction(
                    target_rel,
                    self._file_content,
                )
                or {}
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Simulation Failed",
                str(exc),
            )
            self._publish_event(
                "integration.failed",
                {
                    "stage": "simulation",
                    "target_rel_path": target_rel,
                    "error": str(exc),
                },
            )
            return

        message = (
            "DRY-RUN TRANSACTION SIMULATION\n\n"
            f"Target: {simulation.get('target_path', target_rel)}\n"
            f"Create file: {simulation.get('will_create', 'Unknown')}\n"
            f"Overwrite file: "
            f"{simulation.get('will_overwrite', 'Unknown')}\n"
            f"Compile check: "
            f"{simulation.get('compile_check', 'Unknown')}\n"
            f"Rollback ready: "
            f"{simulation.get('rollback_available', 'Unknown')}\n"
            "Required restarts: "
            f"{', '.join(simulation.get('required_restarts', []) or []) or 'None'}\n\n"
            "No disk writes were performed."
        )

        QMessageBox.information(
            self,
            "Transaction Simulation",
            message,
        )
        self._publish_event(
            "integration.simulation.completed",
            {
                "target_rel_path": target_rel,
                "simulation": simulation,
            },
        )

    def _learn_route(self) -> None:
        if not self._active_file_path or not self._match_info:
            return

        filename = Path(self._active_file_path).name
        target = str(
            self._match_info.get("target_rel_path") or ""
        )
        if not target:
            return

        try:
            self._validate_target_rel(target)
            self.kb.save_learned_route(filename, target)
            self._set_state(
                HubState.ROUTE_CONFIRMED,
                f"Saved '{filename}' → '{target}'",
            )
            self._publish_event(
                "integration.route.learned",
                {
                    "filename": filename,
                    "target_rel_path": target,
                },
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Route Save Failed",
                str(exc),
            )

    def _execute_transaction_flow(self) -> None:
        if (
            not self._active_file_path
            or not self._match_info
            or not self._file_content
        ):
            return

        target_rel = str(
            self._match_info.get("target_rel_path") or ""
        )

        try:
            target_path = self._validate_target_rel(target_rel)
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Transaction Blocked",
                str(exc),
            )
            return

        high_risk = target_rel.replace("\\", "/").lower().startswith(
            HIGH_RISK_PREFIXES
        )
        if high_risk:
            response = QMessageBox.warning(
                self,
                "High-Risk Integration",
                "This change targets a runtime, kernel, core or security "
                "module.\n\n"
                f"Target: {target_rel}\n\n"
                "Continue with the protected transaction?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if response != QMessageBox.Yes:
                return

        response = QMessageBox.question(
            self,
            "Apply Integration Transaction",
            f"Source:\n{self._active_file_path}\n\n"
            f"Target:\n{target_path}\n\n"
            "The transaction will create a backup, apply the change, "
            "compile it, run verification and roll back on failure.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            return

        self._set_busy(True)
        self._set_state(HubState.TRANSACTION_RUNNING)
        self._publish_event(
            "integration.transaction.started",
            {
                "source": self._active_file_path,
                "target_rel_path": target_rel,
            },
        )

        patch_id = f"P-HUB-{Path(self._active_file_path).stem}"
        transaction_id = f"T-HUB-{os.urandom(4).hex()}"

        try:
            transaction = PatchTransaction(
                patch_id=patch_id,
                transaction_id=transaction_id,
                project_root=self.project_root,
                target_rel_path=target_rel,
                new_content=self._file_content,
                audit_service=self.audit_service,
                agent_id="IntegrationHub",
                executor="User/IntegrationHub",
                event_emitter=self._transaction_event_emitter(),
            )

            if not transaction.begin():
                self._transaction_failure(
                    "Preflight or backup creation failed."
                )
                return

            if not transaction.apply_and_compile():
                self._transaction_failure(
                    "Compile failed. Original file restored."
                )
                return

            if not transaction.run_verification():
                self._transaction_failure(
                    "Verification failed. Original file restored."
                )
                return

            commit_result = transaction.commit()
            if commit_result is False:
                self._transaction_failure(
                    "Transaction commit was rejected."
                )
                return

            self._set_state(
                HubState.COMMITTED,
                f"Deployed to {target_rel}",
            )
            self.apply_btn.setEnabled(False)

            try:
                self.kb.reindex()
            except Exception:
                logger.exception(
                    "Repository reindex failed after commit"
                )

            self._publish_event(
                "integration.transaction.committed",
                {
                    "patch_id": patch_id,
                    "transaction_id": transaction_id,
                    "source": self._active_file_path,
                    "target_rel_path": target_rel,
                },
            )
            self.transaction_committed.emit(
                transaction_id,
                target_rel,
            )

            QMessageBox.information(
                self,
                "Integration Complete",
                f"Successfully deployed:\n{target_rel}",
            )
        except Exception as exc:
            logger.exception("Integration transaction failed")
            self._transaction_failure(str(exc))
        finally:
            self._set_busy(False)

    def _transaction_failure(self, message: str) -> None:
        self._set_state(
            HubState.FAILED_ROLLED_BACK,
            message,
        )
        self.apply_btn.setEnabled(self._policy_passed)
        self._publish_event(
            "integration.transaction.rolled_back",
            {
                "target_rel_path": self._match_info.get(
                    "target_rel_path"
                ),
                "error": message,
            },
        )
        self.transaction_failed.emit(message)
        QMessageBox.critical(
            self,
            "Integration Transaction Failed",
            message,
        )

    def _open_target_folder(self) -> None:
        target_rel = self.target_edit.text().strip()
        if not target_rel:
            return

        try:
            target = self._validate_target_rel(target_rel)
            folder = target if target.is_dir() else target.parent
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Open Target Folder",
                str(exc),
            )

    def _reset_ingestion(self, keep_state: bool = False) -> None:
        self._active_file_path = None
        self._match_info = {}
        self._file_content = ""
        self._diff_info = {}
        self._delta = {}
        self._components = []
        self._ai_review = {}
        self._safety_warnings = []
        self._safety_errors = []
        self._policy_passed = False

        if hasattr(self, "target_edit"):
            self.target_edit.blockSignals(True)
            self.target_edit.clear()
            self.target_edit.blockSignals(False)
            self.reset_route_btn.setEnabled(False)
            self.status_text.setText("Awaiting file ingestion...")
            self.diff_preview.clear()
            self.learn_btn.setEnabled(False)
            self.simulate_btn.setEnabled(False)
            self.apply_btn.setEnabled(False)
            self.open_target_btn.setEnabled(False)

        if not keep_state and hasattr(self, "lifecycle_ribbon"):
            self._set_state(HubState.IDLE)
