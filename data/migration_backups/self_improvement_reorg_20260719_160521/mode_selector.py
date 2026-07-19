from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ModeSelector(QFrame):
    """
    Manual / Assisted / Autonomous selector for the Self Improvement panel.

    The widget can operate independently or update a runtime core directly.
    Pass ``runtime_core`` when constructing it to have mode changes forwarded to:

        runtime_core.self_improvement.set_mode(mode)

    Signals
    -------
    mode_changed(str)
        Emitted after a mode has been selected successfully.

    mode_change_failed(str)
        Emitted when the runtime rejects a requested mode change.
    """

    mode_changed = Signal(str)
    mode_change_failed = Signal(str)

    MODES = ("manual", "assisted", "autonomous")

    DISPLAY_NAMES = {
        "manual": "Manual",
        "assisted": "Assisted",
        "autonomous": "Autonomous",
    }

    MODE_DESCRIPTIONS = {
        "manual": "Scan and report findings. No changes are applied.",
        "assisted": "Prepare improvement jobs and wait for approval.",
        "autonomous": "Execute approved low-risk improvements automatically.",
    }

    def __init__(
        self,
        runtime_core=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self._mode = "manual"
        self._buttons: dict[str, QPushButton] = {}

        self.setObjectName("SelfImprovementModeSelector")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._build_ui()
        self._apply_styles()
        self.set_mode(
            self._read_runtime_mode(),
            update_runtime=False,
            emit_signal=False,
        )

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(8)

        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading_row.setSpacing(8)

        title = QLabel("Mode", self)
        title.setObjectName("ModeSelectorTitle")

        self.current_mode_label = QLabel("Manual", self)
        self.current_mode_label.setObjectName("ModeSelectorCurrentMode")

        heading_row.addWidget(title)
        heading_row.addStretch(1)
        heading_row.addWidget(self.current_mode_label)

        root_layout.addLayout(heading_row)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)

        for mode in self.MODES:
            button = QPushButton(
                self.DISPLAY_NAMES[mode],
                self,
            )
            button.setObjectName(
                f"ModeSelectorButton_{mode}"
            )
            button.setCheckable(True)
            button.setCursor(
                button.cursor()
            )
            button.clicked.connect(
                lambda checked=False, selected=mode: (
                    self.set_mode(selected)
                )
            )

            self.button_group.addButton(button)
            self._buttons[mode] = button
            button_row.addWidget(button)

        root_layout.addLayout(button_row)

        self.description_label = QLabel(
            self.MODE_DESCRIPTIONS[self._mode],
            self,
        )
        self.description_label.setObjectName(
            "ModeSelectorDescription"
        )
        self.description_label.setWordWrap(True)
        root_layout.addWidget(self.description_label)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#SelfImprovementModeSelector {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QLabel#ModeSelectorTitle {
                color: #f2f5f8;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#ModeSelectorCurrentMode {
                color: #7dd3fc;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#ModeSelectorDescription {
                color: #98a5b3;
                font-size: 11px;
            }

            QPushButton {
                min-height: 30px;
                padding: 0 12px;
                color: #b8c2cc;
                background-color: #1c2430;
                border: 1px solid #303c4d;
                border-radius: 7px;
                font-size: 11px;
                font-weight: 600;
            }

            QPushButton:hover {
                color: #ffffff;
                background-color: #243142;
                border-color: #3c4e64;
            }

            QPushButton:pressed {
                background-color: #18212c;
            }

            QPushButton:checked {
                color: #ffffff;
                background-color: #2563eb;
                border-color: #3b82f6;
            }

            QPushButton:disabled {
                color: #637080;
                background-color: #171d25;
                border-color: #252e39;
            }
            """
        )

    def _read_runtime_mode(self) -> str:
        service = getattr(
            self.runtime_core,
            "self_improvement",
            None,
        )

        if service is None:
            return self._mode

        status_method = getattr(service, "status", None)
        if callable(status_method):
            try:
                status = status_method() or {}
                mode = str(
                    status.get(
                        "mode",
                        self._mode,
                    )
                ).lower()
                if mode in self.MODES:
                    return mode
            except Exception:
                pass

        mode = str(
            getattr(
                service,
                "mode",
                self._mode,
            )
        ).lower()

        return (
            mode
            if mode in self.MODES
            else self._mode
        )

    def mode(self) -> str:
        """Return the currently selected mode."""
        return self._mode

    def set_runtime_core(self, runtime_core) -> None:
        """
        Attach or replace the runtime core used for mode updates.
        """
        self.runtime_core = runtime_core
        self.refresh_from_runtime()

    def refresh_from_runtime(self) -> None:
        """
        Synchronize the selector with the self-improvement service.
        """
        self.set_mode(
            self._read_runtime_mode(),
            update_runtime=False,
            emit_signal=False,
        )

    def set_mode(
        self,
        mode: str,
        *,
        update_runtime: bool = True,
        emit_signal: bool = True,
    ) -> bool:
        """
        Select a mode and optionally update the runtime service.

        Returns ``True`` when the mode was accepted.
        """
        normalized = str(mode).strip().lower()

        if normalized not in self.MODES:
            message = (
                f"Unsupported self-improvement mode: {mode!r}"
            )
            self.mode_change_failed.emit(message)
            return False

        previous_mode = self._mode

        if update_runtime:
            service = getattr(
                self.runtime_core,
                "self_improvement",
                None,
            )

            setter = getattr(
                service,
                "set_mode",
                None,
            )

            if service is not None and callable(setter):
                try:
                    setter(normalized)
                except Exception as exc:
                    self._set_button_checked(
                        previous_mode
                    )
                    self.mode_change_failed.emit(
                        str(exc)
                    )
                    return False

        self._mode = normalized
        self._set_button_checked(normalized)

        display_name = self.DISPLAY_NAMES[normalized]
        self.current_mode_label.setText(display_name)
        self.description_label.setText(
            self.MODE_DESCRIPTIONS[normalized]
        )

        if emit_signal and normalized != previous_mode:
            self.mode_changed.emit(normalized)

        return True

    def _set_button_checked(
        self,
        mode: str,
    ) -> None:
        button = self._buttons.get(mode)
        if button is None:
            return

        was_blocked = self.button_group.blockSignals(
            True
        )
        button.setChecked(True)
        self.button_group.blockSignals(was_blocked)

    def set_controls_enabled(
        self,
        enabled: bool,
    ) -> None:
        """
        Enable or disable every mode button.
        """
        for button in self._buttons.values():
            button.setEnabled(enabled)

    def set_mode_enabled(
        self,
        mode: str,
        enabled: bool,
    ) -> None:
        """
        Enable or disable one mode option.
        """
        normalized = str(mode).strip().lower()
        button = self._buttons.get(normalized)
        if button is not None:
            button.setEnabled(enabled)
