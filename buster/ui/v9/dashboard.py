from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
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


class DashboardEvolutionSnapshot:
    """
    Lightweight adapter that exposes the same learning state used by the
    Evolution panel without constructing another UI panel.
    """

    def __init__(self, live: Any):
        self.live = live
        self.runtime_core = (
            getattr(live, "kernel_core", None)
            or getattr(live, "runtime_core", None)
            or getattr(live, "core", None)
        )
        self.project_root = self._project_root()

    def collect(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "title": "Level 1 — Operator",
            "level": 1,
            "xp": 0,
            "xp_next": 250,
            "xp_pct": 0,
            "trust": 0.0,
            "permission_rank": "Operator",
            "permissions": [],
            "emotion": "Focused / Analytical",
            "active_goal": "Awaiting active mission state.",
            "drives_matrix": {},
            "skills_tree": {},
            "agents": {},
            "learning_metrics": {},
            "sources": [],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

        self._merge_runtime_state(snapshot)
        self._merge_services(snapshot)
        self._merge_files(snapshot)
        self._derive(snapshot)
        return snapshot

    def _merge_runtime_state(self, snapshot: dict[str, Any]) -> None:
        candidates = [
            self.runtime_core,
            getattr(self.runtime_core, "identity", None)
            if self.runtime_core is not None
            else None,
            getattr(self.runtime_core, "evolution_service", None)
            if self.runtime_core is not None
            else None,
            getattr(self.live, "identity", None),
        ]

        for owner in candidates:
            if owner is None:
                continue

            for method_name in (
                "get_ui_context",
                "get_evolution_state",
                "get_identity_state",
                "get_learning_state",
                "snapshot",
                "get_state",
                "to_dict",
            ):
                method = getattr(owner, method_name, None)
                if not callable(method):
                    continue

                try:
                    value = method()
                except Exception:
                    continue

                if isinstance(value, dict):
                    self._deep_merge(snapshot, value)
                    snapshot["sources"].append(
                        f"{type(owner).__name__}.{method_name}"
                    )
                    break

    def _merge_services(self, snapshot: dict[str, Any]) -> None:
        for name in (
            "learning_engine",
            "learning_memory",
            "experience_store",
            "strategy_store",
            "build_strategies",
            "design_patterns",
            "growth_ledger",
            "evolution_service",
            "autonomy_service",
            "repair_history",
            "rag",
            "context_index",
        ):
            service = self._resolve_service(name)
            if service is None:
                continue

            data = self._service_snapshot(service)
            if not isinstance(data, dict):
                continue

            self._merge_named_source(snapshot, name, data)
            snapshot["sources"].append(name)

    def _merge_files(self, snapshot: dict[str, Any]) -> None:
        data_dir = self.project_root / "data"
        files = {
            "learning_memory": data_dir / "learning_memory.json",
            "build_strategies": data_dir / "build_strategies.json",
            "design_patterns": data_dir / "design_patterns.json",
            "agent_memory": data_dir / "agent_memory.json",
            "autonomy_state": data_dir / "autonomy_state.json",
            "evolution_state": data_dir / "evolution_state.json",
            "execution_history": data_dir / "execution_history.json",
            "code_review_cache": data_dir / "code_review_cache.json",
        }

        for name, path in files.items():
            data = self._read_json(path)
            if data is None:
                continue

            self._merge_named_source(snapshot, name, data)
            snapshot["sources"].append(path.name)

    def _merge_named_source(
        self,
        snapshot: dict[str, Any],
        name: str,
        data: dict[str, Any],
    ) -> None:
        metrics = snapshot.setdefault("learning_metrics", {})

        if name == "evolution_state":
            self._deep_merge(snapshot, data)
            return

        if name in {"learning_memory", "learning_engine"}:
            metrics["lessons"] = max(
                self._number(metrics.get("lessons")),
                self._collection_size(data),
            )
            skills = (
                data.get("skills")
                or data.get("skills_tree")
                or data.get("competencies")
            )
            if isinstance(skills, dict):
                for skill, value in skills.items():
                    if isinstance(value, dict):
                        value = (
                            value.get("percent")
                            or value.get("score")
                            or value.get("level")
                            or 0
                        )
                    snapshot.setdefault("skills_tree", {})[str(skill)] = int(
                        max(0, min(100, self._number(value)))
                    )
            return

        if name == "build_strategies":
            metrics["strategies"] = self._collection_size(data)
            return

        if name == "design_patterns":
            metrics["patterns"] = self._collection_size(data)
            return

        if name in {"execution_history", "repair_history"}:
            successful, failed = self._count_outcomes(data)
            metrics["verified_successes"] = max(
                self._number(metrics.get("verified_successes")),
                successful,
            )
            metrics["failures"] = max(
                self._number(metrics.get("failures")),
                failed,
            )
            return

        if name == "agent_memory":
            agents = data.get("agents") if isinstance(
                data.get("agents"), dict
            ) else data
            if isinstance(agents, dict):
                for key, value in agents.items():
                    if isinstance(value, dict) and any(
                        marker in str(key).lower()
                        for marker in (
                            "agent",
                            "builder",
                            "tester",
                            "fixer",
                            "review",
                            "verifier",
                        )
                    ):
                        snapshot.setdefault("agents", {})[str(key)] = value
            return

        if name in {"autonomy_state", "autonomy_service"}:
            snapshot.setdefault("drives_matrix", {})[
                "autonomy"
            ] = self._extract_percentage(data)
            return

        self._deep_merge(snapshot, data)

    def _derive(self, snapshot: dict[str, Any]) -> None:
        metrics = snapshot.setdefault("learning_metrics", {})
        verified = int(
            self._number(
                metrics.get("verified_successes")
                or metrics.get("successful_repairs")
                or metrics.get("success_count")
            )
        )
        failures = int(
            self._number(
                metrics.get("failures")
                or metrics.get("failed_repairs")
                or metrics.get("failure_count")
            )
        )
        patterns = int(
            self._number(
                metrics.get("patterns")
                or metrics.get("pattern_count")
            )
        )
        strategies = int(
            self._number(
                metrics.get("strategies")
                or metrics.get("strategy_count")
            )
        )
        lessons = int(
            self._number(
                metrics.get("lessons")
                or metrics.get("experience_count")
            )
        )

        total = verified + failures
        trust = snapshot.get("trust") or snapshot.get("trust_factor")
        if isinstance(trust, str):
            trust = self._number(trust)
        if not trust:
            trust = round((verified / total) * 100, 1) if total else 0.0
        snapshot["trust"] = float(trust)

        xp = int(
            snapshot.get("xp")
            or verified * 12
            + lessons * 4
            + patterns * 8
            + strategies * 10
        )
        level = int(snapshot.get("level") or (xp // 250 + 1))
        level = max(1, level)
        xp_floor = (level - 1) * 250
        xp_next = max(level * 250, xp + 1)
        xp_pct = int(
            max(
                0,
                min(
                    100,
                    ((xp - xp_floor) / max(1, xp_next - xp_floor)) * 100,
                ),
            )
        )

        rank = (
            snapshot.get("permission_rank")
            or snapshot.get("rank")
            or self._rank_for_level(level)
        )

        snapshot["xp"] = xp
        snapshot["level"] = level
        snapshot["xp_next"] = xp_next
        snapshot["xp_pct"] = xp_pct
        snapshot["permission_rank"] = rank

        title = str(snapshot.get("title") or "")
        if not title or title == "Level 1 — Operator":
            snapshot["title"] = f"Level {level} — {rank}"

        metrics.update(
            {
                "verified_successes": verified,
                "failures": failures,
                "patterns": patterns,
                "strategies": strategies,
                "lessons": lessons,
                "success_rate": round(
                    verified / total * 100, 1
                )
                if total
                else 0.0,
            }
        )

        skills = snapshot.setdefault("skills_tree", {})
        baseline = {
            "Coding": min(100, 15 + verified * 2),
            "Python": min(100, 15 + verified * 2),
            "PySide6": min(100, 10 + patterns * 3),
            "Git": min(100, 10 + strategies * 4),
            "Repair": min(100, 10 + verified * 3),
            "Testing": min(100, 10 + verified * 2),
            "Architecture": min(100, patterns * 5 + strategies * 4),
            "Automation": min(100, lessons * 2 + strategies * 3),
            "RAG": min(100, lessons * 3),
            "Planning": min(100, strategies * 5),
            "Verification": min(100, verified * 3),
            "Self Improvement": min(
                100, verified * 2 + patterns * 3
            ),
        }
        for skill, value in baseline.items():
            skills.setdefault(skill, int(value))

        drives = snapshot.setdefault("drives_matrix", {})
        drives.setdefault("helping", 75)
        drives.setdefault("builder", min(100, 40 + strategies * 4))
        drives.setdefault("learning", min(100, 45 + lessons * 3))
        drives.setdefault("protection", min(100, 60 + verified * 2))
        drives.setdefault("curiosity", min(100, 45 + patterns * 3))
        drives.setdefault("verification", min(100, 55 + verified * 2))
        drives.setdefault("autonomy", min(100, 20 + trust * 0.7))

    def _resolve_service(self, name: str) -> Any:
        for owner in (self.runtime_core, self.live):
            if owner is None:
                continue

            direct = getattr(owner, name, None)
            if direct is not None:
                return direct

            services = getattr(owner, "services", None)
            if isinstance(services, dict):
                if name in services:
                    return services[name]
            elif services is not None:
                for method_name in ("get", "resolve", "service"):
                    method = getattr(services, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        value = method(name)
                    except Exception:
                        continue
                    if value is not None:
                        return value
        return None

    @staticmethod
    def _service_snapshot(service: Any) -> Optional[dict[str, Any]]:
        if isinstance(service, dict):
            return service

        for method_name in (
            "snapshot",
            "get_state",
            "get_status",
            "get_metrics",
            "to_dict",
            "export",
            "summary",
        ):
            method = getattr(service, method_name, None)
            if not callable(method):
                continue
            try:
                value = method()
            except Exception:
                continue
            if isinstance(value, dict):
                return value

        state = getattr(service, "state", None)
        return state if isinstance(state, dict) else None

    def _project_root(self) -> Path:
        for owner in (
            self.live,
            self.runtime_core,
            getattr(self.live, "core", None),
        ):
            if owner is None:
                continue
            for name in (
                "project_root",
                "workspace_root",
                "repo_root",
                "root_path",
                "root",
            ):
                value = getattr(owner, name, None)
                if value:
                    try:
                        path = Path(value).expanduser().resolve()
                        if path.exists():
                            return path
                    except Exception:
                        continue
        return Path.cwd().resolve()

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists() or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _collection_size(data: Any) -> int:
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            for key in (
                "items",
                "entries",
                "records",
                "experiences",
                "lessons",
                "patterns",
                "strategies",
                "history",
            ):
                value = data.get(key)
                if isinstance(value, (list, dict)):
                    return len(value)
            return len(data)
        return 0

    @staticmethod
    def _count_outcomes(data: Any) -> tuple[int, int]:
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = []
            for key in ("history", "records", "entries", "items", "events"):
                value = data.get(key)
                if isinstance(value, list):
                    records = value
                    break
            if not records:
                records = list(data.values())
        else:
            records = []

        successful = failed = 0
        for item in records:
            if not isinstance(item, dict):
                continue
            state = str(
                item.get("status")
                or item.get("result")
                or item.get("outcome")
                or ""
            ).lower()
            if any(
                word in state
                for word in (
                    "success",
                    "passed",
                    "complete",
                    "committed",
                )
            ):
                successful += 1
            elif any(
                word in state
                for word in (
                    "fail",
                    "error",
                    "rollback",
                    "rejected",
                )
            ):
                failed += 1
        return successful, failed

    @staticmethod
    def _extract_percentage(data: dict[str, Any]) -> int:
        for key in (
            "autonomy_pct",
            "readiness",
            "confidence",
            "progress",
            "score",
        ):
            if key not in data:
                continue
            value = DashboardEvolutionSnapshot._number(data[key])
            if 0 <= value <= 1:
                value *= 100
            return int(max(0, min(100, value)))
        return 0

    @staticmethod
    def _deep_merge(
        target: dict[str, Any],
        source: dict[str, Any],
    ) -> None:
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                DashboardEvolutionSnapshot._deep_merge(
                    target[key],
                    value,
                )
            elif value is not None:
                target[key] = value

    @staticmethod
    def _number(value: Any) -> float:
        try:
            if isinstance(value, str):
                value = value.strip().rstrip("%")
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _rank_for_level(level: int) -> str:
        if level >= 12:
            return "Systems Architect"
        if level >= 9:
            return "Autonomy Engineer"
        if level >= 6:
            return "Senior Builder"
        if level >= 3:
            return "Developer"
        return "Operator"


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
        self.evolution_snapshot = DashboardEvolutionSnapshot(live)
        self._event_unsubscribers: list[Callable[[], None]] = []
        self._last_evolution_state: dict[str, Any] = {}

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
        self._connect_evolution_events()

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
        self.level_val = QLabel("Level 1 — Operator")
        self.level_val.setStyleSheet("font-weight: bold;")
        self.xp_pct_lbl = QLabel("0%")
        self.xp_pct_lbl.setStyleSheet("color: #00FFCC;")
        level_row.addWidget(self.level_val)
        level_row.addStretch()
        level_row.addWidget(self.xp_pct_lbl)
        evo_section.addLayout(level_row)

        self.xp_bar = QProgressBar(self)
        self.xp_bar.setFixedHeight(10)
        self.xp_bar.setRange(0, 100)
        self.xp_bar.setValue(0)
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #333; background: #151515; border-radius: 3px; }
            QProgressBar::chunk { background-color: #00FFCC; }
        """)
        evo_section.addWidget(self.xp_bar)

        # Identity Profiles & Capabilities
        self.permissions_val = QLabel("Permission Level: awaiting capability state")
        self.permissions_val.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        self.permissions_val.setWordWrap(True)
        
        self.trust_val = QLabel("Trust by Capability: 0.0%")
        self.trust_val.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        
        self.mood_val = QLabel("Current Operational State: Focused / Analytical")
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
            ("Curiosity Drive", "curiosity", "#FFBB33"),
            ("Verification", "verification", "#23B8FF"),
            ("Autonomy Ready", "autonomy", "#31D158"),
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
            pbar.setValue(0)
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
        self.goals_val = QLabel("Active Goal: Awaiting active mission state.")
        self.goals_val.setStyleSheet("color: #FFBB33; font-size: 11px; font-style: italic;")
        self.goals_val.setWordWrap(True)
        
        self.skills_val = QLabel("Learned Skills: waiting for learning memory")
        self.skills_val.setStyleSheet("color: #888888; font-size: 11px;")
        self.skills_val.setWordWrap(True)

        self.agents_val = QLabel("Agent Levels: waiting for agent memory")
        self.agents_val.setStyleSheet("color: #00C851; font-size: 10px; font-weight: bold;")

        evo_section.addWidget(self.goals_val)
        evo_section.addWidget(self.skills_val)
        evo_section.addWidget(self.agents_val)

        self.learning_metrics_val = QLabel(
            "Learning: 0 lessons · 0 patterns · 0 strategies · "
            "0 verified outcomes"
        )
        self.learning_metrics_val.setWordWrap(True)
        self.learning_metrics_val.setStyleSheet(
            "color:#23B8FF;font-size:10px;font-weight:700;"
        )
        evo_section.addWidget(self.learning_metrics_val)

        self.evolution_source_val = QLabel(
            "Evolution sources: waiting for runtime and learning stores"
        )
        self.evolution_source_val.setWordWrap(True)
        self.evolution_source_val.setStyleSheet(
            "color:#7894B5;font-size:9px;"
        )
        evo_section.addWidget(self.evolution_source_val)

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
        self._refresh_evolution_state()

        # Core System Telemetry Loop Refresh
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

    def _refresh_evolution_state(self) -> None:
        try:
            state = self.evolution_snapshot.collect()
            self._last_evolution_state = state
        except Exception:
            return

        self.level_val.setText(
            str(state.get("title") or "Level 1 — Operator")
        )

        xp_pct = int(state.get("xp_pct", 0) or 0)
        self.xp_bar.setValue(max(0, min(100, xp_pct)))
        self.xp_pct_lbl.setText(f"{xp_pct}%")

        trust = state.get("trust", 0)
        try:
            trust_text = f"{float(str(trust).rstrip('%')):.1f}%"
        except (TypeError, ValueError):
            trust_text = str(trust)
        self.trust_val.setText(
            f"Trust by Capability: {trust_text}"
        )

        emotion = (
            state.get("emotion")
            or state.get("operational_state")
            or state.get("mood")
            or "Focused / Analytical"
        )
        self.mood_val.setText(
            f"Current Operational State: {emotion}"
        )

        permissions = state.get("permissions", []) or []
        if isinstance(permissions, str):
            permission_text = permissions
        else:
            permission_text = ", ".join(
                str(item) for item in permissions
            )
        if not permission_text:
            permission_text = str(
                state.get("permission_rank")
                or "Operator"
            )
        self.permissions_val.setText(
            f"Permission Level: {permission_text}"
        )

        drives = state.get("drives_matrix", {}) or {}
        for key, bar in self.drive_bars.items():
            raw = drives.get(key, 0)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0
            if 0 <= value <= 1:
                value *= 100
            bar.setValue(int(max(0, min(100, value))))

        goal = (
            state.get("active_goal")
            or state.get("goal")
            or state.get("current_goal")
            or "Awaiting active mission state."
        )
        self.goals_val.setText(f"Active Goal: {goal}")

        skills = state.get("skills_tree", {}) or {}
        ordered_skills = sorted(
            skills.items(),
            key=lambda item: float(
                item[1].get("score", 0)
                if isinstance(item[1], dict)
                else item[1] or 0
            ),
            reverse=True,
        )
        skill_text = ", ".join(
            f"{name} {int(float(value.get('score', 0) if isinstance(value, dict) else value or 0))}%"
            for name, value in ordered_skills[:7]
        )
        self.skills_val.setText(
            "Learned Skills: "
            + (skill_text or "no learned skills recorded")
        )

        agents = state.get("agents", {}) or {}
        agent_parts = []
        for name, data in list(agents.items())[:5]:
            if not isinstance(data, dict):
                continue
            level = int(data.get("level", 1) or 1)
            success = float(
                data.get("success_rate")
                or data.get("success")
                or 0
            )
            agent_parts.append(
                f"{name} Lv.{level} ({success:.0f}%)"
            )
        self.agents_val.setText(
            "Agent Levels: "
            + (" | ".join(agent_parts) or "no agent experience recorded")
        )

        metrics = state.get("learning_metrics", {}) or {}
        self.learning_metrics_val.setText(
            "Learning: "
            f"{int(metrics.get('lessons', 0) or 0)} lessons · "
            f"{int(metrics.get('patterns', 0) or 0)} patterns · "
            f"{int(metrics.get('strategies', 0) or 0)} strategies · "
            f"{int(metrics.get('verified_successes', 0) or 0)} "
            "verified outcomes"
        )

        sources = state.get("sources", []) or []
        source_text = ", ".join(str(item) for item in sources[:5])
        if len(sources) > 5:
            source_text += f" +{len(sources) - 5} more"
        self.evolution_source_val.setText(
            "Evolution sources: "
            + (source_text or "none connected")
        )

    def _connect_evolution_events(self) -> None:
        core = (
            getattr(self.live, "kernel_core", None)
            or getattr(self.live, "runtime_core", None)
            or getattr(self.live, "core", None)
        )
        if core is None:
            return

        candidates = [
            getattr(core, name, None)
            for name in (
                "event_bus",
                "event_router",
                "dispatcher",
                "router",
            )
        ]

        topics = (
            "evolution.changed",
            "level.progressed",
            "experience.recorded",
            "learning.recorded",
            "learning.pattern.created",
            "learning.strategy.created",
            "repair.completed",
            "repair.failed",
            "verification.completed",
            "agent.completed",
            "agent.failed",
            "integration.transaction.committed",
            "plugin.hotpatch.applied",
            "autonomy.changed",
        )

        for bus in candidates:
            if bus is None:
                continue

            for method_name in ("subscribe", "on", "register"):
                method = getattr(bus, method_name, None)
                if not callable(method):
                    continue

                for topic in topics:
                    try:
                        unsubscribe = method(
                            topic,
                            self._on_evolution_event,
                        )
                        if callable(unsubscribe):
                            self._event_unsubscribers.append(
                                unsubscribe
                            )
                    except Exception:
                        continue
                return

    def _on_evolution_event(self, _event: Any) -> None:
        QTimer.singleShot(50, self._refresh_evolution_state)

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
            getattr(self.live, "core", None),
            getattr(self.live, "kernel_core", None),
            getattr(self.live, "runtime_core", None),
        ):
            if owner is None:
                continue

            for name in (
                "project_root",
                "workspace_root",
                "repo_root",
                "root_path",
                "root",
            ):
                root = getattr(owner, name, None)
                if not root:
                    continue

                try:
                    return Path(root).resolve()
                except Exception:
                    continue

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

        for unsubscribe in self._event_unsubscribers:
            try:
                unsubscribe()
            except Exception:
                pass
        self._event_unsubscribers.clear()

        super().closeEvent(event)


class _NotFound:
    pass


_NOT_FOUND = _NotFound()


__all__ = [
    "DashboardWindow",
]