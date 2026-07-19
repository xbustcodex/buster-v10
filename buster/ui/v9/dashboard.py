from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import psutil
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from buster.ui.v9.theme import STYLE


class DashboardWindow(QWidget):
    """
    Compact runtime dashboard.

    The dashboard keeps lightweight system monitoring on its timer, while all
    user actions are explicitly connected to working handlers.
    """

    REFRESH_INTERVAL_MS = 1500

    def __init__(self, live):
        super().__init__()

        self.live = live

        self.setWindowTitle("Dashboard")
        self.resize(520, 520)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setStyleSheet(STYLE)

        self._build_ui()
        self._connect_signals()

        self.timer = QTimer(self)
        self.timer.timeout.connect(
            self.refresh
        )
        self.timer.start(
            self.REFRESH_INTERVAL_MS
        )

        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setObjectName("Title")
        root.addWidget(title)

        self.rows: dict[str, QLabel] = {}

        for label in (
            "CPU",
            "RAM",
            "Disk",
            "AI Mode",
            "Voice",
            "Vision",
            "Git Branch",
            "Project",
        ):
            row = QHBoxLayout()

            left = QLabel(label)
            right = QLabel("checking...")
            right.setStyleSheet(
                "color:#35ff6b;"
            )

            row.addWidget(left)
            row.addStretch()
            row.addWidget(right)

            root.addLayout(row)
            self.rows[label] = right

        buttons = QHBoxLayout()

        self.refresh_button = QPushButton(
            "Refresh"
        )
        self.open_data_button = QPushButton(
            "Open Data"
        )
        self.run_doctor_button = QPushButton(
            "Run Doctor"
        )

        buttons.addWidget(
            self.refresh_button
        )
        buttons.addWidget(
            self.open_data_button
        )
        buttons.addWidget(
            self.run_doctor_button
        )

        root.addLayout(buttons)

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(
            self.refresh
        )
        self.open_data_button.clicked.connect(
            self.open_data_folder
        )
        self.run_doctor_button.clicked.connect(
            self.run_doctor
        )

    # ------------------------------------------------------------------
    # Dashboard refresh
    # ------------------------------------------------------------------

    def refresh(self, *_args) -> None:
        self._set_row(
            "CPU",
            f"{psutil.cpu_percent()}%",
        )

        memory = psutil.virtual_memory()
        self._set_row(
            "RAM",
            f"{memory.percent}%",
        )

        disk_root = self._disk_root()

        try:
            disk = psutil.disk_usage(
                str(disk_root)
            )
            disk_text = (
                f"{round(disk.free / (1024 ** 3), 1)} GB free"
            )
        except Exception:
            disk_text = "unknown"

        self._set_row(
            "Disk",
            disk_text,
        )

        self._set_row(
            "AI Mode",
            self._service_value(
                "ai",
                (
                    "quick_status",
                    "status",
                ),
            ),
        )
        self._set_row(
            "Voice",
            self._service_value(
                "voice",
                ("status",),
            ),
        )
        self._set_row(
            "Vision",
            self._service_value(
                "vision",
                ("status",),
            ),
        )
        self._set_row(
            "Git Branch",
            self._git_branch(),
        )
        self._set_row(
            "Project",
            self._project_root().name,
        )

    def _set_row(
        self,
        name: str,
        value: Any,
    ) -> None:
        label = self.rows.get(name)

        if label is not None:
            label.setText(
                self._display_value(value)
            )

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def open_data_folder(self) -> None:
        data_path = (
            self._project_root()
            / "data"
        )

        try:
            data_path.mkdir(
                parents=True,
                exist_ok=True,
            )
        except Exception as exc:
            self._show_error(
                "Open Data",
                f"Could not create the data folder:\n\n{exc}",
            )
            return

        if self._open_path(data_path):
            return

        self._show_error(
            "Open Data",
            (
                "Windows could not open the data folder:\n\n"
                f"{data_path}"
            ),
        )

    def run_doctor(self) -> None:
        self.run_doctor_button.setEnabled(
            False
        )
        self.run_doctor_button.setText(
            "Running..."
        )

        try:
            result = self._execute_doctor()
            message = self._format_result(
                result
            )

            QMessageBox.information(
                self,
                "Buster Doctor",
                message,
            )

        except Exception as exc:
            self._show_error(
                "Buster Doctor",
                str(exc),
            )

        finally:
            self.run_doctor_button.setText(
                "Run Doctor"
            )
            self.run_doctor_button.setEnabled(
                True
            )
            self.refresh()

    # ------------------------------------------------------------------
    # Doctor discovery
    # ------------------------------------------------------------------

    def _execute_doctor(self) -> Any:
        """
        Locate the available diagnostic API without coupling DashboardWindow
        to one runtime revision.
        """

        candidates: list[
            tuple[Any, tuple[str, ...]]
        ] = [
            (
                self.live,
                (
                    "run_doctor",
                    "doctor",
                    "health",
                ),
            ),
            (
                getattr(
                    self.live,
                    "core",
                    None,
                ),
                (
                    "run_doctor",
                    "doctor",
                    "health",
                ),
            ),
            (
                getattr(
                    self.live,
                    "runtime_core",
                    None,
                ),
                (
                    "run_doctor",
                    "doctor",
                    "health",
                ),
            ),
        ]

        for target, names in candidates:
            result = self._call_first(
                target,
                names,
            )

            if result is not _NOT_FOUND:
                return result

        services = getattr(
            self.live,
            "services",
            None,
        )

        if services is not None:
            for service_name in (
                "lifecycle",
                "health",
                "runtime",
            ):
                service = self._get_service(
                    services,
                    service_name,
                )
                result = self._call_first(
                    service,
                    (
                        "run_doctor",
                        "doctor",
                        "health",
                        "status",
                    ),
                )

                if result is not _NOT_FOUND:
                    return result

        raise RuntimeError(
            "No doctor or health diagnostic service is registered."
        )

    @staticmethod
    def _call_first(
        target: Any,
        names: tuple[str, ...],
    ) -> Any:
        if target is None:
            return _NOT_FOUND

        for name in names:
            method = getattr(
                target,
                name,
                None,
            )

            if callable(method):
                return method()

        return _NOT_FOUND

    # ------------------------------------------------------------------
    # Runtime helpers
    # ------------------------------------------------------------------

    def _service_value(
        self,
        service_name: str,
        methods: tuple[str, ...],
    ) -> str:
        services = getattr(
            self.live,
            "services",
            None,
        )
        service = self._get_service(
            services,
            service_name,
        )

        if service is None:
            return "unknown"

        for method_name in methods:
            method = getattr(
                service,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:
                return self._display_value(
                    method()
                )
            except Exception:
                continue

        return "unknown"

    @staticmethod
    def _get_service(
        services: Any,
        name: str,
    ) -> Any:
        if services is None:
            return None

        getter = getattr(
            services,
            "get",
            None,
        )

        if callable(getter):
            try:
                return getter(name)
            except Exception:
                return None

        if isinstance(services, dict):
            return services.get(name)

        return None

    def _git_branch(self) -> str:
        method = getattr(
            self.live,
            "git_branch",
            None,
        )

        if callable(method):
            try:
                return self._display_value(
                    method()
                )
            except Exception:
                pass

        root = self._project_root()

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "branch",
                    "--show-current",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

            branch = result.stdout.strip()
            return branch or "unknown"

        except Exception:
            return "unknown"

    def _project_root(self) -> Path:
        for owner in (
            self.live,
            getattr(
                self.live,
                "core",
                None,
            ),
            getattr(
                self.live,
                "runtime_core",
                None,
            ),
        ):
            root = getattr(
                owner,
                "root",
                None,
            )

            if root:
                try:
                    return Path(
                        root
                    ).resolve()
                except Exception:
                    pass

        return Path.cwd().resolve()

    @staticmethod
    def _disk_root() -> Path:
        anchor = Path.cwd().anchor

        if anchor:
            return Path(anchor)

        return Path("/")

    @staticmethod
    def _open_path(
        path: Path,
    ) -> bool:
        try:
            if os.name == "nt":
                os.startfile(
                    str(path)
                )
                return True

            return QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(path)
                )
            )

        except Exception:
            return False

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _display_value(
        value: Any,
    ) -> str:
        if value is None:
            return "unknown"

        if isinstance(value, str):
            return value

        if isinstance(
            value,
            (bool, int, float),
        ):
            return str(value)

        if isinstance(
            value,
            dict,
        ):
            for key in (
                "status",
                "state",
                "mode",
                "message",
                "summary",
            ):
                if key in value:
                    return str(value[key])

        return str(value)

    @staticmethod
    def _format_result(
        result: Any,
    ) -> str:
        if result is None:
            return (
                "Doctor completed successfully."
            )

        if isinstance(result, str):
            return result

        if isinstance(
            result,
            (dict, list, tuple),
        ):
            return json.dumps(
                result,
                indent=2,
                default=str,
            )

        to_dict = getattr(
            result,
            "to_dict",
            None,
        )

        if callable(to_dict):
            try:
                return json.dumps(
                    to_dict(),
                    indent=2,
                    default=str,
                )
            except Exception:
                pass

        return str(result)

    def _show_error(
        self,
        title: str,
        message: str,
    ) -> None:
        QMessageBox.critical(
            self,
            title,
            message,
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def closeEvent(
        self,
        event,
    ) -> None:
        self.timer.stop()
        super().closeEvent(event)


class _NotFound:
    pass


_NOT_FOUND = _NotFound()


__all__ = [
    "DashboardWindow",
]
