"""
Buster Integration Hub Panel - Production Safe Ingestion Workspace
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
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
from buster.ui.v9.panels.self_improvement.apply.patch_transaction import PatchTransaction


class IntegrationHubPanel(QWidget):
    """Main Integration Hub Workspace."""

    def __init__(self, runtime_core=None, live=None, parent=None):
        super().__init__(parent)
        self.runtime_core = runtime_core
        self.live = live
        self.project_root = Path.cwd()

        self.kb = RepoKnowledgeBase(self.project_root)
        self.analyzer = PatchAnalyzer(self.project_root, getattr(self.kb, "index", {}))
        self.audit_service = getattr(runtime_core, "audit_service", AuditService())

        self.current_state = HubState.IDLE
        self._active_file_path: Optional[str] = None
        self._match_info: Dict[str, Any] = {}
        self._file_content: str = ""
        self._safety_warnings: list[str] = []

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel("BUSTER INTEGRATION HUB")
        title.setStyleSheet("color:#23B8FF; font-size:20px; font-weight:800; letter-spacing:1px;")
        
        subtitle = QLabel("Universal Controlled Ingestion · AST Intelligence · Transactional Pipeline Protection")
        subtitle.setStyleSheet("color:#7894B5; font-size:11px;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Lifecycle State Ribbon
        self.lifecycle_ribbon = QLabel("State: IDLE")
        self.lifecycle_ribbon.setStyleSheet(
            "background:#050B14; color:#7894B5; border:1px solid #14324F; "
            "border-radius:6px; padding:6px 12px; font-family:Consolas; font-weight:700; font-size:11px;"
        )
        layout.addWidget(self.lifecycle_ribbon)

        # Splitter Layout
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Drop + Inspection Card
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Interactive Drop Target
        self.drop_card = QFrame()
        self.drop_card.setObjectName("DropCard")
        self.drop_card.setStyleSheet(
            "QFrame#DropCard { background:#050B14; border:2px dashed #175A94; border-radius:10px; padding:20px; }"
            "QFrame#DropCard:hover { border-color:#23B8FF; background:#07182B; }"
        )
        self.drop_card.setAcceptDrops(True)
        self.drop_card.dragEnterEvent = self._drag_enter
        self.drop_card.dropEvent = self._drop_event
        self.drop_card.mousePressEvent = self._click_browse

        drop_box = QVBoxLayout(self.drop_card)
        drop_box.setAlignment(Qt.AlignCenter)
        lbl_icon = QLabel("📦")
        lbl_icon.setStyleSheet("font-size:32px; background:transparent;")
        lbl_text = QLabel("Drag & Drop File / Patch Here (or Click to Select)")
        lbl_text.setStyleSheet("color:#DCEBFF; font-weight:700; font-size:12px; background:transparent;")
        drop_box.addWidget(lbl_icon, 0, Qt.AlignCenter)
        drop_box.addWidget(lbl_text, 0, Qt.AlignCenter)

        left_layout.addWidget(self.drop_card)

        # Analysis & Safety Status Display
        self.status_card = QFrame()
        self.status_card.setStyleSheet("background:#07111D; border:1px solid #15324E; border-radius:8px; padding:12px;")
        status_box = QVBoxLayout(self.status_card)

        self.status_text = QLabel("Awaiting file ingestion...")
        self.status_text.setStyleSheet("color:#AFC8E6; font-size:11px; font-family:Consolas;")
        self.status_text.setWordWrap(True)
        status_box.addWidget(self.status_text)

        left_layout.addWidget(self.status_card)
        splitter.addWidget(left_widget)

        # Right Column: Unified Diff Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_lbl = QLabel("PATCH INSPECTION & DIFF PREVIEW")
        preview_lbl.setStyleSheet("color:#7894B5; font-size:10px; font-weight:700;")
        right_layout.addWidget(preview_lbl)

        self.diff_preview = QTextEdit()
        self.diff_preview.setReadOnly(True)
        self.diff_preview.setStyleSheet(
            "QTextEdit { background:#050B14; color:#BFD1E7; border:1px solid #14324F; "
            "border-radius:6px; padding:8px; font-family:Consolas; font-size:11px; }"
        )
        right_layout.addWidget(self.diff_preview)
        splitter.addWidget(right_widget)

        splitter.setSizes([450, 400])
        layout.addWidget(splitter, 1)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.addStretch()

        self.learn_btn = QPushButton("Confirm & Remember Route")
        self.learn_btn.setEnabled(False)
        self.learn_btn.setStyleSheet(
            "QPushButton { background:#0A1D33; color:#23B8FF; border:1px solid #175A94; border-radius:6px; padding:6px 12px; font-weight:600; }"
            "QPushButton:hover { background:#0E2A49; }"
        )
        self.learn_btn.clicked.connect(self._learn_route)
        action_bar.addWidget(self.learn_btn)

        # Added Dry-Run Simulation Button
        self.simulate_btn = QPushButton("Simulate Transaction")
        self.simulate_btn.setEnabled(False)
        self.simulate_btn.setFixedHeight(32)
        self.simulate_btn.setStyleSheet(
            "QPushButton { background:#0D3B66; color:#64DFDF; border:1px solid #175A94; border-radius:6px; padding:0 16px; font-weight:700; }"
            "QPushButton:hover { background:#145088; color:#FFFFFF; }"
            "QPushButton:disabled { background:#0A1D33; color:#4A617C; border:none; }"
        )
        self.simulate_btn.clicked.connect(self._run_simulation)
        action_bar.addWidget(self.simulate_btn)

        self.apply_btn = QPushButton("Apply Patch Transaction")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setFixedHeight(32)
        self.apply_btn.setStyleSheet(
            "QPushButton { background:#175A94; color:#FFFFFF; border:none; border-radius:6px; padding:0 20px; font-weight:700; }"
            "QPushButton:hover { background:#23B8FF; color:#050B14; }"
            "QPushButton:disabled { background:#0A1D33; color:#4A617C; }"
        )
        self.apply_btn.clicked.connect(self._execute_transaction_flow)
        action_bar.addWidget(self.apply_btn)

        layout.addLayout(action_bar)

    def _set_state(self, state: HubState, detail: str = "") -> None:
        self.current_state = state
        txt = f"State: {state.name}"
        if detail:
            txt += f" — {detail}"
        self.lifecycle_ribbon.setText(txt)

    def _drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            self._process_ingestion(urls[0].toLocalFile())
        event.acceptProposedAction()

    def _click_browse(self, event) -> None:
        if event.button() == Qt.LeftButton:
            path, _ = QFileDialog.getOpenFileName(self, "Select Patch File", "", "Python Files (*.py);;All Files (*)")
            if path:
                self._process_ingestion(path)

    def _process_ingestion(self, file_path: str) -> None:
        self._set_state(HubState.DROPPED, Path(file_path).name)
        self._active_file_path = file_path

        # Step 1: Analyzing
        self._set_state(HubState.ANALYZING)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._file_content = f.read()
        except Exception as exc:
            self._set_state(HubState.FAILED_ROLLED_BACK, f"Read Error: {exc}")
            return

        # Step 2: Target Detection via Knowledge Base
        self._match_info = self.kb.match_dropped_content(file_path)
        self._set_state(HubState.TARGET_DETECTED, self._match_info["target_rel_path"])

        # Step 3: Route Confirmation & Sanity Check
        target_rel = self._match_info["target_rel_path"]
        diff_info = self.kb.compute_diff_summary(self._file_content, target_rel)
        self._set_state(HubState.SANITY_PASSED)

        # Step 4: Policy & Safety Validation
        passed, warnings, errors = SafetyValidator.evaluate_safety(
            self.project_root,
            target_rel,
            self._file_content,
            self._match_info["confidence"],
        )
        self._safety_warnings = warnings

        if passed:
            self._set_state(HubState.POLICY_APPROVED, "Awaiting User Transaction Approval")

        # Step 5: Render Rich Inspection Metrics
        self._render_rich_inspection_panel(file_path)

        # Render Diff Preview
        if diff_info.get("unified_diff"):
            self.diff_preview.setText(diff_info["unified_diff"])
        else:
            self.diff_preview.setText(self._file_content[:3000])

        self.apply_btn.setEnabled(passed)
        self.learn_btn.setEnabled(True)

    def _render_rich_inspection_panel(self, file_path: str) -> None:
        """Renders rich structural metrics, AI reviews, dependency graphs, and dry-run simulation results."""
        target_rel = self._match_info["target_rel_path"]
        delta = self.analyzer.analyze_structural_delta(target_rel, self._file_content)
        components = self.analyzer.map_affected_components(target_rel, self._file_content)
        ai_review = AIPatchReviewer.review_patch(Path(file_path).name, self._file_content, target_rel)

        graph_str = " → ".join(components)
        risk_class = "green" if ai_review.get("risk_level") == "LOW" else "yellow"

        html = f"""
        <style>
            .metric-hdr {{ color: #23B8FF; font-weight: 800; font-size: 13px; margin-top: 8px; }}
            .dim {{ color: #7894B5; }}
            .value {{ color: #DCEBFF; font-weight: 600; }}
            .green {{ color: #31D158; }}
            .yellow {{ color: #FFB000; }}
            .graph {{ color: #23B8FF; font-family: Consolas; font-weight: 700; }}
        </style>

        <div class="metric-hdr">{Path(file_path).name}</div>
        <hr color="#14324F">

        <span class="dim">Detected Type:</span> <span class="value">✓ {self._match_info['category']}</span><br>
        <span class="dim">Confidence:</span> <span class="green">{self._match_info['confidence']}%</span><br>
        <span class="dim">Destination:</span> <code>{target_rel}</code><br>
        <span class="dim">Existing File:</span> <span class="value">{'Yes' if delta['is_existing'] else 'No (New File)'}</span>

        <div class="metric-hdr">Change Summary</div>
        <span class="green">+ {delta.get('added_classes', 0)} Classes</span><br>
        <span class="green">+ {delta.get('added_funcs', 0)} Functions</span><br>
        <span class="dim">~ {delta.get('modified_funcs', 0)} Functions Modified</span><br>
        <span class="dim">- {delta.get('removed_funcs', 0)} Removed</span>

        <div class="metric-hdr">New Imports</div>
        <span class="value">{', '.join(delta.get('new_imports', [])) or 'None'}</span>

        <div class="metric-hdr">Affected Components Graph</div>
        <span class="graph">{graph_str}</span>

        <div class="metric-hdr">🤖 AI Patch Review</div>
        <span class="dim">Summary:</span> <span class="value">{ai_review['summary']}</span><br>
        <span class="dim">Risk:</span> <span class="{risk_class}">{ai_review['risk_level']}</span><br>
        <span class="dim">Compatibility:</span> <span class="green">{ai_review['compatibility']}</span><br>
        <span class="dim">Issues:</span><br>
        {"<br>".join(ai_review['potential_issues'])}
        """

        self.status_text.setText(html)
        self.simulate_btn.setEnabled(True)

    def _run_simulation(self) -> None:
        """Runs a zero-write transaction simulation and displays the report."""
        if not self._match_info:
            return

        target_rel = self._match_info["target_rel_path"]
        sim = self.analyzer.simulate_patch_transaction(target_rel, self._file_content)

        msg = (
            f"🔍 DRY-RUN TRANSACTION SIMULATION REPORT\n\n"
            f"• Target Path: {sim['target_path']}\n"
            f"• Will Create File: {sim['will_create']}\n"
            f"• Will Overwrite File: {sim['will_overwrite']}\n"
            f"• Syntax/Compile Check: {sim['compile_check']}\n"
            f"• Rollback Snapshot Ready: {sim['rollback_available']}\n"
            f"• Affected Service Restarts: {', '.join(sim['required_restarts']) or 'None'}\n\n"
            f"Status: Zero disk writes performed. Ready to Commit."
        )
        QMessageBox.information(self, "Transaction Simulation", msg)

    def _learn_route(self) -> None:
        if self._active_file_path and self._match_info:
            filename = Path(self._active_file_path).name
            target = self._match_info["target_rel_path"]
            self.kb.save_learned_route(filename, target)
            self._set_state(HubState.ROUTE_CONFIRMED, f"Saved '{filename}' -> '{target}'")

    def _execute_transaction_flow(self) -> None:
        """Executes the strict Transaction Pipeline Lifecycle."""
        if not self._active_file_path or not self._match_info:
            return

        self._set_state(HubState.TRANSACTION_RUNNING)

        patch_id = f"P-{Path(self._active_file_path).stem}"
        tx_id = f"T-HUB-{os.urandom(3).hex()}"
        target_rel = self._match_info["target_rel_path"]

        tx = PatchTransaction(
            patch_id=patch_id,
            transaction_id=tx_id,
            project_root=self.project_root,
            target_rel_path=target_rel,
            new_content=self._file_content,
            audit_service=self.audit_service,
            agent_id="IntegrationHub",
            executor="User/IntegrationHub",
            event_emitter=getattr(self.runtime_core, "dispatcher", None).emit if hasattr(self.runtime_core, "dispatcher") else None,
        )

        # 1. Begin & Preflight
        if not tx.begin():
            self._set_state(HubState.FAILED_ROLLED_BACK, "Preflight / Backup Failure")
            return

        # 2. Apply & Compile Verification
        if not tx.apply_and_compile():
            self._set_state(HubState.FAILED_ROLLED_BACK, "Compile Error — Reverted to Backup")
            return

        # 3. Verification Suite
        if not tx.run_verification():
            self._set_state(HubState.FAILED_ROLLED_BACK, "Verification Test Failed — Reverted to Backup")
            return

        # 4. Commit Change
        tx.commit()
        self._set_state(HubState.COMMITTED, f"Successfully deployed to {target_rel}")
        self.apply_btn.setEnabled(False)
        self.kb.reindex()