from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(slots=True)
class PreviewDiff:
    """
    Structured representation of a generated code-change preview.

    The dataclass deliberately contains only serialisable data so it can be
    created in a worker thread and safely handed back to the UI through a Qt
    signal.
    """

    patch: str
    file_path: str = ""
    title: str = "Generated Patch"
    summary: str = ""
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    validation_state: str = "pending"
    validation_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.patch = str(self.patch or "")
        self.file_path = str(self.file_path or "")
        self.title = str(self.title or "Generated Patch")
        self.summary = str(self.summary or "")
        self.validation_state = str(
            self.validation_state or "pending"
        ).lower()
        self.validation_message = str(
            self.validation_message or ""
        )

        if self.additions <= 0 and self.deletions <= 0 and self.patch:
            additions, deletions = self.count_changes(self.patch)
            self.additions = additions
            self.deletions = deletions

        if self.changed_files <= 0 and self.patch:
            self.changed_files = self.count_files(self.patch)

    @classmethod
    def from_value(cls, value: Any) -> "PreviewDiff":
        """
        Convert a PreviewDiff, mapping, dataclass-like object, or raw patch
        string into a PreviewDiff instance.
        """
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            return cls(patch=value)

        if hasattr(value, "to_dict") and callable(value.to_dict):
            value = value.to_dict()

        if isinstance(value, dict):
            patch = (
                value.get("patch")
                or value.get("diff")
                or value.get("unified_diff")
                or value.get("preview")
                or ""
            )

            return cls(
                patch=str(patch),
                file_path=str(
                    value.get("file_path")
                    or value.get("file")
                    or value.get("path")
                    or ""
                ),
                title=str(
                    value.get("title")
                    or value.get("name")
                    or "Generated Patch"
                ),
                summary=str(
                    value.get("summary")
                    or value.get("description")
                    or ""
                ),
                additions=_to_int(value.get("additions")),
                deletions=_to_int(value.get("deletions")),
                changed_files=_to_int(
                    value.get("changed_files")
                    or value.get("files_changed")
                ),
                validation_state=str(
                    value.get("validation_state")
                    or value.get("validation")
                    or value.get("status")
                    or "pending"
                ),
                validation_message=str(
                    value.get("validation_message")
                    or value.get("message")
                    or ""
                ),
                metadata=dict(value.get("metadata") or {}),
            )

        return cls(
            patch=str(value),
            title=type(value).__name__,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch": self.patch,
            "file_path": self.file_path,
            "title": self.title,
            "summary": self.summary,
            "additions": self.additions,
            "deletions": self.deletions,
            "changed_files": self.changed_files,
            "validation_state": self.validation_state,
            "validation_message": self.validation_message,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def count_changes(patch: str) -> tuple[int, int]:
        additions = 0
        deletions = 0

        for line in patch.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1

        return additions, deletions

    @staticmethod
    def count_files(patch: str) -> int:
        paths: set[str] = set()

        for line in patch.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                path = line[4:].strip().split("\t", 1)[0]
                if path and path != "/dev/null":
                    paths.add(path)

        if paths:
            return len(paths)

        return 1 if patch.strip() else 0


class ValidationBadge(QFrame):
    """
    Compact validation indicator used by PreviewDiffPanel.
    """

    VALID_STATES = {
        "pending",
        "valid",
        "invalid",
        "warning",
        "running",
        "unknown",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._state = "pending"
        self._message = ""

        self.setObjectName("ValidationBadge")
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._dot = QLabel("●", self)
        self._dot.setObjectName("ValidationBadgeDot")
        layout.addWidget(self._dot)

        self._label = QLabel("Pending validation", self)
        self._label.setObjectName("ValidationBadgeText")
        layout.addWidget(self._label)

        self.set_state("pending")

    @property
    def state(self) -> str:
        return self._state

    @property
    def message(self) -> str:
        return self._message

    def set_state(
        self,
        state: str,
        message: str = "",
    ) -> None:
        state = str(state or "unknown").lower().strip()

        aliases = {
            "success": "valid",
            "passed": "valid",
            "pass": "valid",
            "ok": "valid",
            "error": "invalid",
            "failed": "invalid",
            "fail": "invalid",
            "busy": "running",
            "checking": "running",
        }
        state = aliases.get(state, state)

        if state not in self.VALID_STATES:
            state = "unknown"

        self._state = state
        self._message = str(message or "")

        labels = {
            "pending": "Pending validation",
            "valid": "Validation passed",
            "invalid": "Validation failed",
            "warning": "Validation warning",
            "running": "Validating...",
            "unknown": "Validation unknown",
        }

        self._label.setText(labels[state])
        self.setToolTip(self._message)

        self.setProperty("validationState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class DiffStatsCard(QFrame):
    """
    Summary card showing the size and scope of the generated patch.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("DiffStatsCard")

        root = QGridLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setHorizontalSpacing(18)
        root.setVerticalSpacing(3)

        self._files_value = self._make_value_label("0")
        self._additions_value = self._make_value_label("0")
        self._deletions_value = self._make_value_label("0")
        self._lines_value = self._make_value_label("0")

        root.addWidget(
            self._make_caption("FILES"),
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        root.addWidget(
            self._make_caption("ADDITIONS"),
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        root.addWidget(
            self._make_caption("DELETIONS"),
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        root.addWidget(
            self._make_caption("TOTAL"),
            0,
            3,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        root.addWidget(
            self._files_value,
            1,
            0,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        root.addWidget(
            self._additions_value,
            1,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        root.addWidget(
            self._deletions_value,
            1,
            2,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        root.addWidget(
            self._lines_value,
            1,
            3,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        for column in range(4):
            root.setColumnStretch(column, 1)

    def set_stats(
        self,
        additions: int = 0,
        deletions: int = 0,
        changed_files: int = 0,
    ) -> None:
        additions = max(0, int(additions or 0))
        deletions = max(0, int(deletions or 0))
        changed_files = max(0, int(changed_files or 0))

        self._files_value.setText(str(changed_files))
        self._additions_value.setText(f"+{additions}")
        self._deletions_value.setText(f"-{deletions}")
        self._lines_value.setText(str(additions + deletions))

        self._additions_value.setProperty("statType", "additions")
        self._deletions_value.setProperty("statType", "deletions")

        for widget in (
            self._additions_value,
            self._deletions_value,
        ):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def clear(self) -> None:
        self.set_stats()

    def _make_caption(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("DiffStatCaption")
        return label

    def _make_value_label(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("DiffStatValue")
        return label


class DiffViewer(QPlainTextEdit):
    """
    Read-only unified-diff viewer with lightweight line colouring.
    """

    copy_requested = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._patch = ""

        self.setObjectName("DiffViewer")
        self.setReadOnly(True)
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * 4
        )
        self.setPlaceholderText(
            "Generated patch preview will appear here."
        )

        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.setFont(font)

    @property
    def patch(self) -> str:
        return self._patch

    def set_diff(self, patch: str) -> None:
        self._patch = str(patch or "")
        self.setPlainText(self._patch)
        self._apply_diff_formatting()
        self.moveCursor(QTextCursor.MoveOperation.Start)

    def clear_diff(self) -> None:
        self._patch = ""
        self.clear()

    def copy_patch(self) -> None:
        if not self._patch:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(self._patch)
        self.copy_requested.emit(self._patch)

    def _apply_diff_formatting(self) -> None:
        if not self._patch:
            return

        document = self.document()
        block = document.firstBlock()

        while block.isValid():
            text = block.text()
            fmt = QTextCharFormat()

            if text.startswith("diff --git "):
                fmt.setForeground(Qt.GlobalColor.cyan)
                fmt.setFontWeight(QFont.Weight.Bold)
            elif text.startswith("@@"):
                fmt.setForeground(Qt.GlobalColor.magenta)
                fmt.setFontWeight(QFont.Weight.DemiBold)
            elif text.startswith("+++") or text.startswith("---"):
                fmt.setForeground(Qt.GlobalColor.yellow)
                fmt.setFontWeight(QFont.Weight.DemiBold)
            elif text.startswith("+"):
                fmt.setForeground(Qt.GlobalColor.green)
            elif text.startswith("-"):
                fmt.setForeground(Qt.GlobalColor.red)
            elif text.startswith("index "):
                fmt.setForeground(Qt.GlobalColor.gray)

            if fmt.isValid():
                cursor = QTextCursor(block)
                cursor.select(
                    QTextCursor.SelectionType.LineUnderCursor
                )
                cursor.mergeCharFormat(fmt)

            block = block.next()


class PreviewDiffPanel(QFrame):
    """
    Standalone reusable UI for previewing and approving generated patches.

    Signals emit the current PreviewDiff so the parent controller can decide
    how to generate, apply, verify, reject, or persist changes.
    """

    apply_requested = Signal(object)
    verify_requested = Signal(object)
    reject_requested = Signal(object)
    copy_patch_requested = Signal(object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._preview: Optional[PreviewDiff] = None
        self._busy = False

        self.setObjectName("PreviewDiffPanel")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._build_ui()
        self._apply_styles()
        self.clear()

    @property
    def preview(self) -> Optional[PreviewDiff]:
        return self._preview

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)

        title_group = QVBoxLayout()
        title_group.setSpacing(2)

        self.title_label = QLabel("PREVIEW DIFF", self)
        self.title_label.setObjectName("PreviewDiffTitle")
        title_group.addWidget(self.title_label)

        self.path_label = QLabel("No generated patch", self)
        self.path_label.setObjectName("PreviewDiffPath")
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        title_group.addWidget(self.path_label)

        header.addLayout(title_group, 1)

        self.validation_badge = ValidationBadge(self)
        header.addWidget(
            self.validation_badge,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        root.addLayout(header)

        self.summary_label = QLabel("", self)
        self.summary_label.setObjectName("PreviewDiffSummary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        root.addWidget(self.summary_label)

        self.stats_card = DiffStatsCard(self)
        root.addWidget(self.stats_card)

        self.diff_viewer = DiffViewer(self)
        self.diff_viewer.copy_requested.connect(
            self._emit_copy_requested
        )
        root.addWidget(self.diff_viewer, 1)

        self.busy_label = QLabel("", self)
        self.busy_label.setObjectName("PreviewDiffBusy")
        self.busy_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.busy_label.setVisible(False)
        root.addWidget(self.busy_label)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.copy_button = QPushButton("Copy Patch", self)
        self.copy_button.setObjectName("CopyPatchButton")
        self.copy_button.clicked.connect(self._copy_patch)
        actions.addWidget(self.copy_button)

        actions.addItem(
            QSpacerItem(
                0,
                0,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
        )

        self.reject_button = QPushButton("Reject", self)
        self.reject_button.setObjectName("RejectDiffButton")
        self.reject_button.clicked.connect(
            self._emit_reject_requested
        )
        actions.addWidget(self.reject_button)

        self.verify_button = QPushButton("Verify", self)
        self.verify_button.setObjectName("VerifyDiffButton")
        self.verify_button.clicked.connect(
            self._emit_verify_requested
        )
        actions.addWidget(self.verify_button)

        self.apply_button = QPushButton("Apply Changes", self)
        self.apply_button.setObjectName("ApplyDiffButton")
        self.apply_button.clicked.connect(
            self._emit_apply_requested
        )
        actions.addWidget(self.apply_button)

        root.addLayout(actions)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#PreviewDiffPanel {
                background-color: #10151d;
                border: 1px solid #263241;
                border-radius: 10px;
            }

            QLabel#PreviewDiffTitle {
                color: #23B8FF;
                font-size: 13px;
                font-weight: 800;
            }

            QLabel#PreviewDiffPath {
                color: #94a3b8;
                font-size: 10px;
            }

            QLabel#PreviewDiffSummary {
                color: #cbd5e1;
                background-color: #141b24;
                border: 1px solid #263241;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }

            QLabel#PreviewDiffBusy {
                color: #93c5fd;
                background-color: #111827;
                border: 1px solid #1e3a5f;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                font-weight: 700;
            }

            QFrame#DiffStatsCard {
                background-color: #141b24;
                border: 1px solid #263241;
                border-radius: 8px;
            }

            QLabel#DiffStatCaption {
                color: #64748b;
                font-size: 9px;
                font-weight: 800;
            }

            QLabel#DiffStatValue {
                color: #e2e8f0;
                font-size: 14px;
                font-weight: 800;
            }

            QLabel#DiffStatValue[statType="additions"] {
                color: #4ade80;
            }

            QLabel#DiffStatValue[statType="deletions"] {
                color: #f87171;
            }

            QPlainTextEdit#DiffViewer {
                background-color: #0b1017;
                color: #cbd5e1;
                border: 1px solid #263241;
                border-radius: 8px;
                selection-background-color: #1d4ed8;
                padding: 8px;
            }

            QFrame#ValidationBadge {
                border: 1px solid #475569;
                border-radius: 10px;
                background-color: #17202b;
            }

            QFrame#ValidationBadge[validationState="valid"] {
                border-color: #166534;
                background-color: #102419;
            }

            QFrame#ValidationBadge[validationState="invalid"] {
                border-color: #991b1b;
                background-color: #2a1114;
            }

            QFrame#ValidationBadge[validationState="warning"] {
                border-color: #a16207;
                background-color: #2a2110;
            }

            QFrame#ValidationBadge[validationState="running"] {
                border-color: #1d4ed8;
                background-color: #111f3d;
            }

            QLabel#ValidationBadgeDot {
                color: #94a3b8;
                font-size: 10px;
            }

            QFrame#ValidationBadge[validationState="valid"]
            QLabel#ValidationBadgeDot {
                color: #4ade80;
            }

            QFrame#ValidationBadge[validationState="invalid"]
            QLabel#ValidationBadgeDot {
                color: #f87171;
            }

            QFrame#ValidationBadge[validationState="warning"]
            QLabel#ValidationBadgeDot {
                color: #facc15;
            }

            QFrame#ValidationBadge[validationState="running"]
            QLabel#ValidationBadgeDot {
                color: #60a5fa;
            }

            QLabel#ValidationBadgeText {
                color: #cbd5e1;
                font-size: 10px;
                font-weight: 700;
            }

            QPushButton {
                background-color: #1f2937;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 13px;
                font-size: 10px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #273449;
                border-color: #475569;
            }

            QPushButton:pressed {
                background-color: #182131;
            }

            QPushButton:disabled {
                background-color: #151c26;
                color: #59677a;
                border-color: #263241;
            }

            QPushButton#ApplyDiffButton {
                background-color: #166534;
                border-color: #15803d;
            }

            QPushButton#ApplyDiffButton:hover {
                background-color: #15803d;
            }

            QPushButton#VerifyDiffButton {
                background-color: #1d4ed8;
                border-color: #2563eb;
            }

            QPushButton#VerifyDiffButton:hover {
                background-color: #2563eb;
            }

            QPushButton#RejectDiffButton {
                background-color: #3a1d24;
                border-color: #7f1d1d;
            }

            QPushButton#RejectDiffButton:hover {
                background-color: #7f1d1d;
            }
            """
        )

    @Slot(object)
    def show_diff(self, value: Any) -> None:
        """
        Display a PreviewDiff, mapping, object with to_dict(), or raw string.
        """
        preview = PreviewDiff.from_value(value)
        self._preview = preview

        self.title_label.setText(
            preview.title.upper() if preview.title else "PREVIEW DIFF"
        )

        path_text = preview.file_path or self._derive_path(preview.patch)
        self.path_label.setText(path_text or "Generated patch")

        self.summary_label.setText(preview.summary)
        self.summary_label.setVisible(bool(preview.summary.strip()))

        self.diff_viewer.set_diff(preview.patch)
        self.stats_card.set_stats(
            additions=preview.additions,
            deletions=preview.deletions,
            changed_files=preview.changed_files,
        )

        self.set_validation(
            preview.validation_state,
            preview.validation_message,
        )
        self.set_busy(False)
        self._update_actions()

    @Slot()
    def clear(self) -> None:
        self._preview = None

        self.title_label.setText("PREVIEW DIFF")
        self.path_label.setText("No generated patch")
        self.summary_label.clear()
        self.summary_label.setVisible(False)

        self.diff_viewer.clear_diff()
        self.stats_card.clear()
        self.validation_badge.set_state("pending")

        self.busy_label.clear()
        self.busy_label.setVisible(False)

        self._busy = False
        self._update_actions()

    @Slot(bool)
    @Slot(bool, str)
    def set_busy(
        self,
        busy: bool,
        message: str = "Generating preview...",
    ) -> None:
        self._busy = bool(busy)

        self.busy_label.setText(str(message or "Working..."))
        self.busy_label.setVisible(self._busy)

        if self._busy:
            self.validation_badge.set_state(
                "running",
                str(message or ""),
            )

        self._update_actions()

    @Slot(str)
    @Slot(str, str)
    def set_validation(
        self,
        state: str,
        message: str = "",
    ) -> None:
        self.validation_badge.set_state(state, message)

        if self._preview is not None:
            self._preview.validation_state = (
                self.validation_badge.state
            )
            self._preview.validation_message = str(
                message or ""
            )

        self._update_actions()

    def _update_actions(self) -> None:
        has_preview = (
            self._preview is not None
            and bool(self._preview.patch.strip())
        )

        self.copy_button.setEnabled(
            has_preview and not self._busy
        )
        self.reject_button.setEnabled(
            has_preview and not self._busy
        )
        self.verify_button.setEnabled(
            has_preview and not self._busy
        )

        validation_state = self.validation_badge.state
        can_apply = validation_state not in {
            "invalid",
            "running",
        }

        self.apply_button.setEnabled(
            has_preview and not self._busy and can_apply
        )

    @Slot()
    def _copy_patch(self) -> None:
        self.diff_viewer.copy_patch()

    @Slot(str)
    def _emit_copy_requested(self, _patch: str) -> None:
        if self._preview is not None:
            self.copy_patch_requested.emit(self._preview)

    @Slot()
    def _emit_apply_requested(self) -> None:
        if self._preview is not None and not self._busy:
            self.apply_requested.emit(self._preview)

    @Slot()
    def _emit_verify_requested(self) -> None:
        if self._preview is not None and not self._busy:
            self.verify_requested.emit(self._preview)

    @Slot()
    def _emit_reject_requested(self) -> None:
        if self._preview is not None and not self._busy:
            self.reject_requested.emit(self._preview)

    @staticmethod
    def _derive_path(patch: str) -> str:
        for line in patch.splitlines():
            if line.startswith("+++ "):
                path = line[4:].strip().split("\t", 1)[0]
                if path != "/dev/null":
                    return path
        return ""


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


__all__ = [
    "PreviewDiff",
    "ValidationBadge",
    "DiffStatsCard",
    "DiffViewer",
    "PreviewDiffPanel",
]
