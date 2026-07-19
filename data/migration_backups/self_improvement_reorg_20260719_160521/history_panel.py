from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .backup_manager import BackupManager
from .change_manifest import ChangeManifest
from .rollback_manager import RollbackManager


class HistoryPanel(QFrame):
    """
    Transactional Self Improvement history.

    Sources:
        1. ChangeManifest files managed by BackupManager
        2. Legacy self_improvement_history.json
        3. Legacy execution_history.json

    Signals:
        history_selected(dict)
        history_activated(dict)
        rollback_completed(dict)
    """

    history_selected = Signal(dict)
    history_activated = Signal(dict)
    rollback_completed = Signal(dict)

    HEADERS = [
        "Status",
        "Verification",
        "Title",
        "Files",
        "Strategy",
        "Finished",
    ]

    STATUS = {
        "completed": ("SUCCESS", "#22c55e"),
        "success": ("SUCCESS", "#22c55e"),
        "applied": ("APPLIED", "#38bdf8"),
        "verified": ("VERIFIED", "#22c55e"),
        "failed": ("FAILED", "#ef4444"),
        "error": ("ERROR", "#ef4444"),
        "rolled_back": ("ROLLBACK", "#f59e0b"),
        "rollback_failed": ("ROLLBACK FAILED", "#ef4444"),
        "running": ("RUNNING", "#38bdf8"),
        "pending": ("PENDING", "#94a3b8"),
    }

    VERIFY_STATUS = {
        "passed": ("PASS", "#22c55e"),
        "success": ("PASS", "#22c55e"),
        "warning": ("WARN", "#f59e0b"),
        "failed": ("FAIL", "#ef4444"),
        "error": ("ERROR", "#ef4444"),
        "rolled_back": ("ROLLED BACK", "#f59e0b"),
        "pending": ("PENDING", "#94a3b8"),
        "not_run": ("NOT RUN", "#64748b"),
    }

    def __init__(
        self,
        runtime_core=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.history: list[dict[str, Any]] = []

        self.setObjectName("SelfImprovementHistoryPanel")

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()

        title = QLabel("History", self)
        title.setObjectName("HistoryTitle")
        header.addWidget(title)

        self.summary = QLabel("No history", self)
        self.summary.setObjectName("HistorySummary")
        header.addWidget(self.summary)

        header.addStretch(1)

        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button)

        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Vertical, self)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        header_view.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        header_view.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        header_view.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        header_view.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        header_view.setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )

        self.table.itemSelectionChanged.connect(
            self._selection_changed
        )
        self.table.cellDoubleClicked.connect(
            self._double_clicked
        )

        splitter.addWidget(self.table)

        details_frame = QFrame(self)
        details_frame.setObjectName("HistoryDetailsFrame")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(8)

        self.details_title = QLabel(
            "Select a history record",
            details_frame,
        )
        self.details_title.setObjectName("HistoryDetailsTitle")
        details_layout.addWidget(self.details_title)

        self.details = QTextEdit(details_frame)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(
            "Verification, changed files, manifest and rollback "
            "information will appear here."
        )
        details_layout.addWidget(self.details, 1)

        buttons = QHBoxLayout()

        self.view_diff_button = QPushButton(
            "View Diff",
            details_frame,
        )
        self.view_diff_button.clicked.connect(self._view_diff)
        buttons.addWidget(self.view_diff_button)

        self.view_manifest_button = QPushButton(
            "View Manifest",
            details_frame,
        )
        self.view_manifest_button.clicked.connect(
            self._view_manifest
        )
        buttons.addWidget(self.view_manifest_button)

        self.view_verification_button = QPushButton(
            "View Verification",
            details_frame,
        )
        self.view_verification_button.clicked.connect(
            self._view_verification
        )
        buttons.addWidget(self.view_verification_button)

        self.rollback_button = QPushButton(
            "Rollback",
            details_frame,
        )
        self.rollback_button.setObjectName("RollbackButton")
        self.rollback_button.clicked.connect(
            self._rollback_selected
        )
        buttons.addWidget(self.rollback_button)

        self.export_button = QPushButton(
            "Export",
            details_frame,
        )
        self.export_button.clicked.connect(
            self._export_selected
        )
        buttons.addWidget(self.export_button)

        buttons.addStretch(1)
        details_layout.addLayout(buttons)

        splitter.addWidget(details_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([420, 260])

        layout.addWidget(splitter, 1)

        self._set_action_enabled(False)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementHistoryPanel {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QFrame#HistoryDetailsFrame {
                background-color: #111827;
                border: 1px solid #293548;
                border-radius: 8px;
            }

            QLabel#HistoryTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#HistorySummary {
                color: #94a3b8;
                font-size: 11px;
            }

            QLabel#HistoryDetailsTitle {
                color: #23b8ff;
                font-size: 12px;
                font-weight: 700;
            }

            QTableWidget,
            QTextEdit {
                background-color: #111827;
                color: #dbe3eb;
                border: 1px solid #293548;
                font-size: 11px;
            }

            QTableWidget::item:selected {
                background-color: #1d4ed8;
                color: white;
            }

            QTableWidget::item:alternate {
                background-color: #131c2a;
            }

            QHeaderView::section {
                background-color: #1f2937;
                color: #cbd5e1;
                padding: 6px;
                border: none;
                font-weight: 700;
            }

            QPushButton {
                background-color: #1f2937;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #2563eb;
            }

            QPushButton:disabled {
                color: #64748b;
                background-color: #18202b;
                border-color: #263241;
            }

            QPushButton#RollbackButton:hover {
                background-color: #b45309;
            }
            """
        )

    @Slot()
    def refresh(self) -> None:
        records: list[dict[str, Any]] = []

        records.extend(self._load_manifest_history())

        service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )

        if service is not None:
            history_file = getattr(
                service,
                "history_path",
                None,
            )
            if history_file:
                records.extend(self._load_file(history_file))

        root = self._project_root()

        records.extend(
            self._load_file(
                root / "data" / "self_improvement_history.json"
            )
        )
        records.extend(
            self._load_file(
                root / "data" / "execution_history.json"
            )
        )

        self.set_history(self._deduplicate(records))

    def set_history(
        self,
        history: Iterable[Any],
    ) -> None:
        self.history = [
            self._normalise_item(item)
            for item in history
        ]

        self.history.sort(
            key=self._sort_timestamp,
            reverse=True,
        )

        self._render()

    def selected_history(
        self,
    ) -> Optional[dict[str, Any]]:
        row = self.table.currentRow()

        if row < 0 or row >= len(self.history):
            return None

        return self.history[row]

    def clear(self) -> None:
        self.history = []
        self.table.setRowCount(0)
        self.summary.setText("No history")
        self.details.clear()
        self.details_title.setText("Select a history record")
        self._set_action_enabled(False)

    def _render(self) -> None:
        self.table.setRowCount(len(self.history))

        for row, item in enumerate(self.history):
            status = self._status_value(item)
            status_label, status_color = self.STATUS.get(
                status,
                (status.upper(), "#94a3b8"),
            )

            status_item = self._colored_item(
                status_label,
                status_color,
            )
            self.table.setItem(row, 0, status_item)

            verify_status = self._verification_status(item)
            verify_label, verify_color = self.VERIFY_STATUS.get(
                verify_status,
                (verify_status.upper(), "#94a3b8"),
            )
            self.table.setItem(
                row,
                1,
                self._colored_item(
                    verify_label,
                    verify_color,
                ),
            )

            self.table.setItem(
                row,
                2,
                self._item(
                    item.get("title")
                    or item.get("message")
                    or "Self Improvement"
                ),
            )

            files = self._files(item)
            self.table.setItem(
                row,
                3,
                self._item(str(len(files))),
            )

            self.table.setItem(
                row,
                4,
                self._item(
                    item.get("strategy")
                    or item.get("strategy_name")
                    or item.get("provider")
                    or ""
                ),
            )

            self.table.setItem(
                row,
                5,
                self._item(self._finished_at(item)),
            )

        count = len(self.history)
        verified = sum(
            1
            for item in self.history
            if self._verification_status(item) == "passed"
        )
        rolled_back = sum(
            1
            for item in self.history
            if self._status_value(item) == "rolled_back"
        )

        self.summary.setText(
            f"{count} record(s) · {verified} verified · "
            f"{rolled_back} rolled back"
        )

        if not self.history:
            self.details.clear()
            self.details_title.setText(
                "Select a history record"
            )
            self._set_action_enabled(False)

    @Slot()
    def _selection_changed(self) -> None:
        item = self.selected_history()

        if item:
            self._show_details(item)
            self.history_selected.emit(dict(item))
        else:
            self._set_action_enabled(False)

    @Slot(int, int)
    def _double_clicked(
        self,
        row: int,
        column: int,
    ) -> None:
        del column

        if 0 <= row < len(self.history):
            item = self.history[row]
            self._show_details(item)
            self.history_activated.emit(dict(item))

    def _show_details(
        self,
        item: Mapping[str, Any],
    ) -> None:
        change_id = str(
            item.get("change_id")
            or item.get("id")
            or "Legacy record"
        )

        self.details_title.setText(
            f"{item.get('title') or 'Self Improvement'} · {change_id}"
        )

        lines = [
            f"Change ID: {change_id}",
            f"Status: {self._status_value(item).replace('_', ' ').title()}",
            f"Verification: {self._verification_status(item).replace('_', ' ').title()}",
            f"Finished: {self._finished_at(item) or 'Unknown'}",
        ]

        provider = str(item.get("provider") or "")
        model = str(item.get("model") or "")

        if provider or model:
            lines.append(
                "AI: "
                + " / ".join(
                    value
                    for value in (provider, model)
                    if value
                )
            )

        summary = str(
            item.get("summary")
            or item.get("message")
            or ""
        ).strip()

        if summary:
            lines.extend(["", "Summary", summary])

        files = self._files(item)
        if files:
            lines.extend(["", "Files"])
            for file_info in files:
                lines.append(
                    f"• {self._file_display(file_info)}"
                )

        verification = self._verification(item)
        checks = verification.get("checks", [])

        if checks:
            lines.extend(["", "Verification Checks"])

            for check in checks:
                if not isinstance(check, Mapping):
                    continue

                status = str(
                    check.get("status") or "unknown"
                ).upper()
                name = str(
                    check.get("name")
                    or check.get("checker")
                    or "Check"
                )
                summary_text = str(
                    check.get("summary")
                    or check.get("message")
                    or ""
                )

                line = f"• [{status}] {name}"
                if summary_text:
                    line += f": {summary_text}"
                lines.append(line)

        rollback = item.get("rollback")
        if isinstance(rollback, Mapping):
            lines.extend(["", "Rollback"])
            lines.append(
                str(
                    rollback.get("message")
                    or rollback.get("summary")
                    or rollback.get("status")
                    or "Rollback information recorded."
                )
            )

        manifest_path = str(
            item.get("manifest_path") or ""
        )
        if manifest_path:
            lines.extend(
                ["", f"Manifest: {manifest_path}"]
            )

        self.details.setPlainText("\n".join(lines))
        self._set_action_enabled(True)

        can_rollback = bool(
            item.get("can_rollback", True)
        )
        is_manifest = bool(item.get("change_id"))
        already_rolled_back = (
            self._status_value(item) == "rolled_back"
        )

        self.rollback_button.setEnabled(
            can_rollback
            and is_manifest
            and not already_rolled_back
        )
        self.view_diff_button.setEnabled(
            bool(item.get("patch"))
        )
        self.view_verification_button.setEnabled(
            bool(self._verification(item))
        )
        self.view_manifest_button.setEnabled(
            is_manifest
        )

    @Slot()
    def _view_diff(self) -> None:
        item = self.selected_history()
        if not item:
            return

        patch = str(item.get("patch") or "").strip()

        if not patch:
            self._message(
                "View Diff",
                "No saved patch is available for this record.",
            )
            return

        self._show_text_dialog(
            "Saved Patch",
            patch,
        )

    @Slot()
    def _view_manifest(self) -> None:
        item = self.selected_history()
        if not item:
            return

        self._show_text_dialog(
            "Change Manifest",
            json.dumps(item, indent=2, ensure_ascii=False),
        )

    @Slot()
    def _view_verification(self) -> None:
        item = self.selected_history()
        if not item:
            return

        verification = self._verification(item)

        if not verification:
            self._message(
                "Verification",
                "No verification report is available.",
            )
            return

        self._show_text_dialog(
            "Verification Report",
            json.dumps(
                verification,
                indent=2,
                ensure_ascii=False,
            ),
        )

    @Slot()
    def _rollback_selected(self) -> None:
        item = self.selected_history()
        if not item:
            return

        change_id = str(item.get("change_id") or "")
        if not change_id:
            self._message(
                "Rollback",
                "This legacy history record has no ChangeManifest.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Rollback Change",
            "Restore all files from the verified backup for "
            f"change {change_id}?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.rollback_button.setEnabled(False)
        self.details.append(
            "\n\nRollback requested..."
        )

        try:
            manager = self._backup_manager()
            manifest = manager.load_manifest(change_id)

            result = RollbackManager(
                project_root=self._project_root(),
                backup_manager=manager,
            ).rollback(
                manifest,
                verify=True,
                save_manifest=True,
            )

            result_dict = self._to_dict(result)

            if bool(result_dict.get("success")):
                self._message(
                    "Rollback Complete",
                    "The selected change was restored successfully.",
                )
            else:
                errors = "\n".join(
                    str(error)
                    for error in (
                        result_dict.get("errors") or []
                    )
                )
                self._message(
                    "Rollback Failed",
                    errors
                    or "Rollback did not complete successfully.",
                    warning=True,
                )

            self.rollback_completed.emit(result_dict)
            self.refresh()

        except Exception as exc:
            self._message(
                "Rollback Failed",
                str(exc),
                warning=True,
            )
            self.rollback_button.setEnabled(True)

    @Slot()
    def _export_selected(self) -> None:
        item = self.selected_history()
        if not item:
            return

        change_id = str(
            item.get("change_id")
            or item.get("id")
            or "history"
        )

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History Record",
            f"buster_change_{change_id}.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if not path:
            return

        try:
            Path(path).write_text(
                json.dumps(
                    item,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self._message(
                "Export Complete",
                f"History record exported to:\n{path}",
            )
        except Exception as exc:
            self._message(
                "Export Failed",
                str(exc),
                warning=True,
            )

    def _load_manifest_history(
        self,
    ) -> list[dict[str, Any]]:
        manager = self._backup_manager()
        records: list[dict[str, Any]] = []

        manifests = self._list_manifests(manager)

        for manifest_value in manifests:
            try:
                manifest = self._manifest_from_value(
                    manifest_value,
                    manager,
                )
                record = manifest.to_dict()
                record["manifest_path"] = str(
                    manager.manifest_path(
                        manifest.change_id
                    )
                )
                record["_source"] = "manifest"
                records.append(record)
            except Exception:
                continue

        return records

    @staticmethod
    def _list_manifests(
        manager: BackupManager,
    ) -> list[Any]:
        for name in (
            "list_manifests",
            "manifests",
            "history",
        ):
            method = getattr(manager, name, None)

            if callable(method):
                try:
                    values = method()
                    if values is not None:
                        return list(values)
                except Exception:
                    pass

        roots = []

        for name in (
            "manifests_root",
            "manifest_root",
            "history_root",
            "backup_root",
        ):
            value = getattr(manager, name, None)
            if value:
                roots.append(Path(value))

        project_root = Path(
            getattr(manager, "project_root", ".")
        )

        roots.extend(
            [
                project_root
                / "data"
                / "self_improvement"
                / "manifests",
                project_root
                / "data"
                / "self_improvement_history"
                / "manifests",
                project_root / "data" / "history" / "manifests",
                project_root / ".buster" / "history" / "manifests",
            ]
        )

        seen: set[str] = set()
        paths: list[Path] = []

        for root in roots:
            try:
                root = root.expanduser().resolve()
            except Exception:
                continue

            key = str(root).lower()
            if key in seen or not root.exists():
                continue

            seen.add(key)
            paths.extend(root.glob("*.json"))

        return paths

    @staticmethod
    def _manifest_from_value(
        value: Any,
        manager: BackupManager,
    ) -> ChangeManifest:
        if isinstance(value, ChangeManifest):
            return value

        if isinstance(value, Mapping):
            return ChangeManifest.from_value(value)

        path = Path(str(value))

        if path.exists():
            return ChangeManifest.load(path)

        return manager.load_manifest(str(value))

    def _backup_manager(self) -> BackupManager:
        return BackupManager(
            project_root=self._project_root()
        )

    def _project_root(self) -> Path:
        return Path(
            getattr(
                self.runtime_core,
                "root",
                ".",
            )
        ).expanduser().resolve()

    @staticmethod
    def _verification(
        item: Mapping[str, Any],
    ) -> dict[str, Any]:
        value = item.get("verification")

        if isinstance(value, Mapping):
            return dict(value)

        value = item.get("verification_report")
        if isinstance(value, Mapping):
            return dict(value)

        return {}

    def _verification_status(
        self,
        item: Mapping[str, Any],
    ) -> str:
        if self._status_value(item) == "rolled_back":
            return "rolled_back"

        verification = self._verification(item)

        if not verification:
            return "not_run"

        if verification.get("passed") is True:
            return "passed"

        if verification.get("passed") is False:
            return "failed"

        status = str(
            verification.get("status") or ""
        ).lower()

        if status in self.VERIFY_STATUS:
            return status

        checks = verification.get("checks")
        if isinstance(checks, list):
            statuses = {
                str(check.get("status") or "").lower()
                for check in checks
                if isinstance(check, Mapping)
            }

            if statuses & {"failed", "error"}:
                return "failed"

            if statuses & {"warning"}:
                return "warning"

            if statuses and statuses <= {
                "passed",
                "skipped",
            }:
                return "passed"

        return "pending"

    @staticmethod
    def _status_value(
        item: Mapping[str, Any],
    ) -> str:
        value = str(
            item.get("status")
            or item.get("state")
            or "completed"
        ).lower()

        if item.get("rolled_back") is True:
            return "rolled_back"

        rollback = item.get("rollback")
        if isinstance(rollback, Mapping):
            if rollback.get("success") is True:
                return "rolled_back"

        return value

    @staticmethod
    def _files(
        item: Mapping[str, Any],
    ) -> list[Any]:
        files = item.get("files")

        if isinstance(files, list):
            return files

        targets = item.get("targets")
        if isinstance(targets, list):
            return targets

        file_path = (
            item.get("file_path")
            or item.get("file")
            or item.get("path")
        )

        return [file_path] if file_path else []

    @staticmethod
    def _file_display(
        value: Any,
    ) -> str:
        if isinstance(value, Mapping):
            path = (
                value.get("path")
                or value.get("file_path")
                or value.get("file")
                or "Unknown file"
            )
            status = str(value.get("status") or "").strip()

            return (
                f"{path} ({status})"
                if status
                else str(path)
            )

        return str(value)

    @staticmethod
    def _finished_at(
        item: Mapping[str, Any],
    ) -> str:
        value = (
            item.get("finished_at")
            or item.get("completed_at")
            or item.get("updated_at")
            or item.get("created_at")
            or ""
        )

        return str(value)

    @classmethod
    def _sort_timestamp(
        cls,
        item: Mapping[str, Any],
    ) -> str:
        return cls._finished_at(item)

    @staticmethod
    def _deduplicate(
        records: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        seen: set[str] = set()

        for record in records:
            item = dict(record)
            key = str(
                item.get("change_id")
                or item.get("id")
                or (
                    f"{item.get('title')}|"
                    f"{item.get('finished_at')}|"
                    f"{item.get('completed_at')}"
                )
            )

            if key in seen:
                continue

            seen.add(key)
            output.append(item)

        return output

    @staticmethod
    def _normalise_item(
        item: Any,
    ) -> dict[str, Any]:
        if isinstance(item, Mapping):
            return dict(item)

        if hasattr(item, "to_dict"):
            try:
                return dict(item.to_dict())
            except Exception:
                pass

        return {
            "title": str(item),
            "status": "completed",
        }

    @staticmethod
    def _load_file(
        path: Any,
    ) -> list[dict[str, Any]]:
        try:
            file_path = Path(path)

            if not file_path.exists():
                return []

            data = json.loads(
                file_path.read_text(encoding="utf-8")
            )

            if isinstance(data, list):
                return [
                    dict(item)
                    for item in data
                    if isinstance(item, Mapping)
                ]

            if isinstance(data, Mapping):
                values = (
                    data.get("history")
                    or data.get("records")
                    or data.get("items")
                    or []
                )

                if isinstance(values, list):
                    return [
                        dict(item)
                        for item in values
                        if isinstance(item, Mapping)
                    ]

            return []

        except Exception:
            return []

    @staticmethod
    def _item(
        value: Any,
    ) -> QTableWidgetItem:
        return QTableWidgetItem(str(value or ""))

    @staticmethod
    def _colored_item(
        value: str,
        color: str,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(value)
        item.setForeground(
            QBrush(QColor(color))
        )
        return item

    def _set_action_enabled(
        self,
        enabled: bool,
    ) -> None:
        for button in (
            self.view_diff_button,
            self.view_manifest_button,
            self.view_verification_button,
            self.rollback_button,
            self.export_button,
        ):
            button.setEnabled(enabled)

    def _show_text_dialog(
        self,
        title: str,
        text: str,
    ) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(title)
        dialog.setDetailedText(text)
        dialog.setIcon(
            QMessageBox.Icon.Information
        )
        dialog.exec()

    def _message(
        self,
        title: str,
        message: str,
        *,
        warning: bool = False,
    ) -> None:
        if warning:
            QMessageBox.warning(
                self,
                title,
                message,
            )
        else:
            QMessageBox.information(
                self,
                title,
                message,
            )

    @staticmethod
    def _to_dict(
        value: Any,
    ) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)

        if hasattr(value, "to_dict"):
            try:
                result = value.to_dict()
                if isinstance(result, Mapping):
                    return dict(result)
            except Exception:
                pass

        return {
            "success": bool(value),
            "message": str(value),
        }


__all__ = [
    "HistoryPanel",
]
