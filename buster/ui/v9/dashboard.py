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
    QProgressBar,
    QScrollArea,
    QFrame,
)

from buster.ui.v9.theme import STYLE


class DashboardWindow(QWidget):
    """
    Compact runtime dashboard updated with Evolution Core metrics.

    The dashboard keeps lightweight system monitoring on its timer, while all
    user actions are explicitly connected to working handlers.
    """

    REFRESH_INTERVAL_MS = 1500

    def __init__(self, live):
        super().__init__()

        self.live = live

        self.setWindowTitle("Dashboard")
        # Expanded slightly to elegantly contain evolution metrics with system logs
        self.resize(540, 680)
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
        root.setContentsMargins(0, 0, 0, 0)

        # Scroll area prevents clipping on low-resolution or tight display scales
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title = QLabel("Dashboard")
        title.setObjectName("Title")
        layout.addWidget(title)

        # ------------------------------------------------------------------
        # BUSTER EVOLUTION BLOCK
        # ------------------------------------------------------------------
        evo_section = QVBoxLayout()
        evo_section.setSpacing(6)

        evo_hdr = QLabel("BUSTER EVOLUTION")
        evo_hdr.setStyleSheet("font-weight: bold; color: #00FFCC; font-size: 13px; letter-spacing: 0.5px;")
        evo_section.addWidget(evo_hdr)

        # Level & Progress Bar
        level_row = QHBoxLayout()
        self.level_val = QLabel("Level 12 — Engineer")
        self.level_val.setStyleSheet("font-weight: bold;")
        self.xp_pct_lbl = QLabel("78%")
        self.xp_pct_lbl.setStyleSheet("color: #00FFCC;")
        level_row.addWidget(self.level_val)
        level_row.addStretch()
        level_row.addWidget(self.xp_pct_lbl)
        evo_section.addLayout(level_row)

        self.xp_bar = QProgressBar(self)
        self.xp_bar.setFixedHeight(10)
        self.xp_bar.setRange(0, 100)
        self.xp_bar.setValue(78)
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #333; background: #151515; border-radius: 3px; }
            QProgressBar::chunk { background-color: #00FFCC; }
        """)
        evo_section.addWidget(self.xp_bar)

        # Identity Profiles & Capabilities
        self.permissions_val = QLabel("Permission Level: Local Git, Python Execution, File Refactoring")
        self.permissions_val.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        self.permissions_val.setWordWrap(True)
        
        self.trust_val = QLabel("Trust by Capability: 94% Core Trust Metric Factor")
        self.trust_val.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        
        self.mood_val = QLabel("Current Emotional State: Focused / Analytical")
        self.mood_val.setStyleSheet("color: #AA66CC; font-size: 11px; font-weight: 500;")

        evo_section.addWidget(self.permissions_val)
        evo_section.addWidget(self.trust_val)
        evo_section.addWidget(self.mood_val)

        # Core Drives Configuration Subgrid
        self.drive_bars: dict[str, QProgressBar] = {}
        drives = [
            ("Helping Drive", "helping", "#4285F4"),
            ("Builder Drive", "builder", "#00C851"),
            ("Learning Drive", "learning", "#AA66CC"),
            ("Protection Drive", "protection", "#FF4444"),
            ("Curiosity Drive", "curiosity", "#FFBB33")
        ]
        
        drives_layout = QVBoxLayout()
        drives_layout.setSpacing(4)
        for d_lbl, d_key, d_color in drives:
            d_row = QHBoxLayout()
            lbl = QLabel(d_lbl)
            lbl.setStyleSheet("font-size: 11px; color: #888;")
            lbl.setMinimumWidth(95)
            
            pbar = QProgressBar(self)
            pbar.setFixedHeight(6)
            pbar.setRange(0, 100)
            pbar.setValue(60)
            pbar.setTextVisible(False)
            pbar.setStyleSheet(f"""
                QProgressBar {{ background: #151515; border: none; border-radius: 1px; }}
                QProgressBar::chunk {{ background-color: {d_color}; }}
            """)
            d_row.addWidget(lbl)
            d_row.addWidget(pbar)
            drives_layout.addLayout(d_row)
            self.drive_bars[d_key] = pbar
            
        evo_section.addLayout(drives_layout)

        # Active Goals, Learned Skills & Agent Levels
        self.goals_val = QLabel("Active Goal: Resolving missing runtime UI components in workspace updates.")
        self.goals_val.setStyleSheet("color: #FFBB33; font-size: 11px; font-style: italic;")
        self.goals_val.setWordWrap(True)
        
        self.skills_val = QLabel("Learned Skills: Python, PySide6, Git Automation, Diagnostics, Sub-agents")
        self.skills_val.setStyleSheet("color: #888888; font-size: 11px;")
        self.skills_val.setWordWrap(True)

        self.agents_val = QLabel("Agent Levels: Builder Agent Lv.3 | Fixer Agent Lv.2 | Reviewer Agent Lv.1")
        self.agents_val.setStyleSheet("color: #00C851; font-size: 10px; font-weight: bold;")

        evo_section.addWidget(self.goals_val)
        evo_section.addWidget(self.skills_val)
        evo_section.addWidget(self.agents_val)

        layout.addLayout(evo_section)

        # Visual Structural Separation Line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #333; margin: 4px 0;")
        layout.addWidget(sep)

        # ------------------------------------------------------------------
        # TELEMETRY MONITORING GRID[cite: 12]
        # ------------------------------------------------------------------
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

            layout.addLayout(row)
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

        layout.addLayout(buttons)
        
        scroll.setWidget(container)
        root.addWidget(scroll)

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
    # Dashboard refresh[cite: 12]
    # ------------------------------------------------------------------

    def refresh(self, *_args) -> None:
        # Dynamic internal extraction hook if runtime context offers structural variables
        if hasattr(self.live, "runtime_core") and hasattr(self.live.runtime_core, "identity"):
            ctx = self.live.runtime_core.identity.get_ui_context()
            self.level_val.setText(ctx.get("title", "Level 12 — Engineer"))
            self.xp_bar.setValue(ctx.get("xp_pct", 78))
            self.xp_pct_lbl.setText(f"{ctx.get('xp_pct', 78)}%")
            self.trust_val.setText(f"Trust by Capability: {ctx.get('trust_factor', '94%')}")
            self.mood_val.setText(f"Current Emotional State: {ctx.get('emotion', 'Focused')}")
            
            drives_matrix = ctx.get("drives_matrix", {})
            for key, bar in self.drive_bars.items():
                bar.setValue(drives_matrix.get(key, 65))

        # Core System Telemetry Loop Refresh[cite: 12]
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
    # Button actions[cite: 12]
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
    # Doctor discovery[cite: 12]
    # ------------------------------------------------------------------

    def _execute_doctor(self) -> Any:
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
    # Runtime helpers[cite: 12]
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
    # Formatting[cite: 12]
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
    # Shutdown[cite: 12]
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