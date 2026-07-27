# buster/ui/v9/panels/evolution_panel/evolution_panel.py
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QTimer, Qt, QTime, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from buster.ui.v9.panels.evolution_panel.drive_card import DriveCard
from buster.ui.v9.panels.evolution_panel.level_card import LevelCard
from buster.ui.v9.panels.evolution_panel.skills_card import SkillsCard

logger = logging.getLogger(__name__)


class EvolutionPanel(QWidget):
    """
    Live evolution and learning dashboard.

    The panel is deliberately read-only. It observes the active runtime,
    learning services and persisted learning stores without owning or
    mutating Buster's intelligence.
    """

    evolution_snapshot_updated = Signal(dict)

    def __init__(self, live=None, runtime_core=None, parent=None):
        super().__init__(parent)
        self.live = live
        self.runtime_core = (
            runtime_core
            or getattr(live, "kernel_core", None)
            or getattr(live, "runtime_core", None)
        )
        self.project_root = self._resolve_project_root()
        self._event_unsubscribers: list[Callable[[], None]] = []
        self._last_snapshot: dict[str, Any] = {}

        self.init_ui()
        self.connect_events()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.refresh_snapshot)
        self.refresh_timer.start()

        QTimer.singleShot(0, self.refresh_snapshot)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def init_ui(self) -> None:
        self.setObjectName("EvolutionPanel")
        self.setStyleSheet(
            """
            QWidget#EvolutionPanel {
                background:#0B1726;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }
            QFrame#EvolutionCard {
                background:#0E1D2E;
                border:1px solid #244560;
                border-radius:9px;
            }
            QPushButton {
                background:#17334E;
                color:#E8F2FC;
                border:1px solid #2B587B;
                border-radius:6px;
                padding:6px 12px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#204B70;
                border-color:#23B8FF;
            }
            QListWidget {
                background:#081522;
                color:#C7D8EA;
                border:1px solid #244560;
                border-radius:6px;
                font-family:Consolas;
                font-size:11px;
                padding:5px;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
        )

        container = QWidget()
        container.setStyleSheet("background:#0B1726;")
        content_layout = QVBoxLayout(container)
        content_layout.setSpacing(11)
        content_layout.setContentsMargins(16, 14, 16, 16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel("BUSTER EVOLUTION SYSTEM")
        title.setStyleSheet(
            "color:#23B8FF;font-size:20px;font-weight:900;"
            "letter-spacing:1px;background:transparent;"
        )
        subtitle = QLabel(
            "Experience · learned skills · repair outcomes · strategies · "
            "patterns · agent growth · autonomy readiness"
        )
        subtitle.setStyleSheet(
            "color:#9EB6CF;font-size:11px;background:transparent;"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.source_status = QLabel("● Learning sources pending")
        self.source_status.setStyleSheet(
            "color:#FFB000;font-weight:700;background:transparent;"
        )
        header.addWidget(self.source_status)

        self.refresh_btn = QPushButton("Refresh Learning State")
        self.refresh_btn.clicked.connect(self.refresh_snapshot)
        header.addWidget(self.refresh_btn)

        content_layout.addLayout(header)

        self.level_card = LevelCard(container)
        self.drive_card = DriveCard(container)
        self.skills_card = SkillsCard(container)

        for card in (
            self.level_card,
            self.drive_card,
            self.skills_card,
        ):
            card.setObjectName("EvolutionCard")

        content_layout.addWidget(self.level_card)
        content_layout.addWidget(self.drive_card)
        content_layout.addWidget(self.skills_card)

        timeline_frame = QFrame()
        timeline_frame.setObjectName("EvolutionCard")
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.setContentsMargins(13, 12, 13, 13)

        timeline_header = QHBoxLayout()
        timeline_label = QLabel("EVOLUTION & LEARNING EVENT LOG")
        timeline_label.setStyleSheet(
            "color:#9EB6CF;font-size:10px;font-weight:800;"
            "letter-spacing:1px;background:transparent;"
        )
        timeline_header.addWidget(timeline_label)
        timeline_header.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.timeline_log_clear)
        timeline_header.addWidget(clear_btn)
        timeline_layout.addLayout(timeline_header)

        self.timeline_log = QListWidget()
        self.timeline_log.setMinimumHeight(150)
        self.timeline_log.document = lambda: None
        timeline_layout.addWidget(self.timeline_log)

        content_layout.addWidget(timeline_frame)
        content_layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Snapshot collection
    # ------------------------------------------------------------------

    @Slot()
    def refresh_snapshot(self) -> None:
        try:
            snapshot = self._collect_snapshot()
            self._last_snapshot = snapshot
            self.refresh_identity_telemetry(snapshot)
            self.evolution_snapshot_updated.emit(snapshot)

            source_count = len(snapshot.get("sources", []))
            self.source_status.setText(
                f"● {source_count} learning source(s) connected"
            )
            self.source_status.setStyleSheet(
                "color:#31D158;font-weight:700;background:transparent;"
                if source_count
                else "color:#FFB000;font-weight:700;background:transparent;"
            )
        except Exception as exc:
            logger.exception("Evolution snapshot refresh failed")
            self.source_status.setText("● Learning refresh failed")
            self.source_status.setStyleSheet(
                "color:#FF6961;font-weight:700;background:transparent;"
            )
            self._add_timeline_entry(f"Refresh failed: {exc}")

    def _collect_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "title": "Level 1 — Operator",
            "level": 1,
            "xp": 0,
            "xp_next": 100,
            "xp_pct": 0,
            "trust": 0.0,
            "permission_rank": "Operator",
            "permissions": [],
            "next_unlock": "Accumulate verified successful work.",
            "drives_matrix": {},
            "skills_tree": {},
            "skill_details": {},
            "agents": {},
            "learning_metrics": {},
            "sources": [],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

        self._merge_runtime_identity(snapshot)
        self._merge_learning_services(snapshot)
        self._merge_persisted_learning(snapshot)
        self._derive_growth_metrics(snapshot)
        return snapshot

    def _merge_runtime_identity(self, snapshot: dict[str, Any]) -> None:
        for owner in self._runtime_candidates():
            for method_name in (
                "get_evolution_state",
                "get_identity_state",
                "get_learning_state",
                "get_status",
                "snapshot",
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

    def _merge_learning_services(self, snapshot: dict[str, Any]) -> None:
        names = (
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
        )

        for name in names:
            service = self._resolve_service(name)
            if service is None:
                continue

            data = self._service_snapshot(service)
            if isinstance(data, dict):
                self._merge_service_data(snapshot, name, data)
                snapshot["sources"].append(name)

    def _merge_persisted_learning(self, snapshot: dict[str, Any]) -> None:
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
            self._merge_service_data(snapshot, name, data)
            snapshot["sources"].append(path.name)

    def _derive_growth_metrics(self, snapshot: dict[str, Any]) -> None:
        metrics = snapshot.setdefault("learning_metrics", {})
        skills = snapshot.setdefault("skills_tree", {})
        details = snapshot.setdefault("skill_details", {})

        verified = self._number(
            metrics.get("verified_successes")
            or metrics.get("successful_repairs")
            or metrics.get("success_count")
        )
        failures = self._number(
            metrics.get("failures")
            or metrics.get("failed_repairs")
            or metrics.get("failure_count")
        )
        patterns = self._number(
            metrics.get("patterns")
            or metrics.get("design_patterns")
            or metrics.get("pattern_count")
        )
        strategies = self._number(
            metrics.get("strategies")
            or metrics.get("build_strategies")
            or metrics.get("strategy_count")
        )
        lessons = self._number(
            metrics.get("lessons")
            or metrics.get("experiences")
            or metrics.get("experience_count")
        )

        total = verified + failures
        trust = snapshot.get("trust")
        if not trust:
            trust = round((verified / total) * 100, 1) if total else 0.0
            snapshot["trust"] = trust

        xp = int(snapshot.get("xp") or (verified * 12 + lessons * 4 + patterns * 8))
        level = max(1, int(snapshot.get("level") or (xp // 250 + 1)))
        xp_floor = (level - 1) * 250
        xp_next = level * 250
        xp_pct = int(
            max(0, min(100, ((xp - xp_floor) / max(1, xp_next - xp_floor)) * 100))
        )

        snapshot["xp"] = xp
        snapshot["level"] = level
        snapshot["xp_next"] = xp_next
        snapshot["xp_pct"] = xp_pct

        rank = self._rank_for_level(level)
        snapshot.setdefault("permission_rank", rank)
        if not snapshot.get("title") or snapshot["title"].startswith("Level 1"):
            snapshot["title"] = f"Level {level} — {rank}"

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
            "Self Improvement": min(100, verified * 2 + patterns * 3),
        }
        for name, value in baseline.items():
            skills.setdefault(name, int(value))
            details.setdefault(name, {})

        drives = snapshot.setdefault("drives_matrix", {})
        drives.setdefault("helping", 75)
        drives.setdefault("builder", min(100, 40 + strategies * 4))
        drives.setdefault("learning", min(100, 45 + lessons * 3))
        drives.setdefault("protection", min(100, 60 + verified * 2))
        drives.setdefault("curiosity", min(100, 45 + patterns * 3))
        drives.setdefault("verification", min(100, 55 + verified * 2))
        drives.setdefault("autonomy", min(100, 20 + trust * 0.7))

        metrics.update(
            {
                "verified_successes": verified,
                "failures": failures,
                "patterns": patterns,
                "strategies": strategies,
                "lessons": lessons,
                "success_rate": round(
                    verified / total * 100, 1
                ) if total else 0.0,
            }
        )

    # ------------------------------------------------------------------
    # Data adapters
    # ------------------------------------------------------------------

    def _merge_service_data(
        self,
        snapshot: dict[str, Any],
        name: str,
        data: Any,
    ) -> None:
        if not isinstance(data, dict):
            return

        if name == "evolution_state":
            self._deep_merge(snapshot, data)
            return

        metrics = snapshot.setdefault("learning_metrics", {})

        if name in {"learning_memory", "learning_engine"}:
            entries = self._collection_size(data)
            metrics["lessons"] = max(
                self._number(metrics.get("lessons")),
                entries,
            )
            self._merge_skill_map(snapshot, data)
        elif name == "build_strategies":
            metrics["strategies"] = self._collection_size(data)
        elif name == "design_patterns":
            metrics["patterns"] = self._collection_size(data)
        elif name in {"execution_history", "repair_history"}:
            success, failed = self._count_outcomes(data)
            metrics["verified_successes"] = max(
                self._number(metrics.get("verified_successes")),
                success,
            )
            metrics["failures"] = max(
                self._number(metrics.get("failures")),
                failed,
            )
        elif name == "agent_memory":
            agents = self._extract_agents(data)
            snapshot.setdefault("agents", {}).update(agents)
        elif name in {"autonomy_state", "autonomy_service"}:
            autonomy = self._extract_percentage(data)
            snapshot.setdefault("drives_matrix", {})["autonomy"] = autonomy
        else:
            self._deep_merge(snapshot, data)

    def _merge_skill_map(
        self,
        snapshot: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        candidates = (
            data.get("skills")
            or data.get("skills_tree")
            or data.get("competencies")
        )
        if isinstance(candidates, dict):
            for key, value in candidates.items():
                if isinstance(value, dict):
                    level = (
                        value.get("percent")
                        or value.get("score")
                        or value.get("level")
                        or 0
                    )
                    snapshot["skill_details"][str(key)] = value
                else:
                    level = value
                snapshot["skills_tree"][str(key)] = int(
                    max(0, min(100, self._number(level)))
                )

    @staticmethod
    def _extract_agents(data: dict[str, Any]) -> dict[str, Any]:
        agents = data.get("agents") if isinstance(data.get("agents"), dict) else data
        result = {}
        for key, value in agents.items():
            if not isinstance(value, dict):
                continue
            if any(
                marker in key.lower()
                for marker in ("agent", "builder", "tester", "fixer", "review", "verifier")
            ):
                result[str(key)] = value
        return result

    @staticmethod
    def _extract_percentage(data: dict[str, Any]) -> int:
        for key in (
            "autonomy_pct",
            "readiness",
            "confidence",
            "progress",
            "score",
        ):
            if key in data:
                value = EvolutionPanel._number(data[key])
                if value <= 1:
                    value *= 100
                return int(max(0, min(100, value)))
        return 0

    @staticmethod
    def _count_outcomes(data: Any) -> tuple[int, int]:
        items = EvolutionPanel._flatten_records(data)
        success = failed = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            state = str(
                item.get("status")
                or item.get("result")
                or item.get("outcome")
                or ""
            ).lower()
            if any(word in state for word in ("success", "passed", "complete", "committed")):
                success += 1
            elif any(word in state for word in ("fail", "error", "rollback", "rejected")):
                failed += 1
        return success, failed

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
    def _flatten_records(data: Any) -> list[Any]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("history", "records", "entries", "items", "events"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
            return list(data.values())
        return []

    def _service_snapshot(self, service: Any) -> Optional[dict[str, Any]]:
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
                    if callable(method):
                        try:
                            value = method(name)
                        except Exception:
                            continue
                        if value is not None:
                            return value
        return None

    def _runtime_candidates(self) -> list[Any]:
        candidates = []
        for owner in (self.runtime_core, self.live):
            if owner is None:
                continue
            candidates.append(owner)
            for name in (
                "evolution_service",
                "learning_engine",
                "identity",
                "growth_ledger",
            ):
                value = getattr(owner, name, None)
                if value is not None:
                    candidates.append(value)
        return candidates

    def _resolve_project_root(self) -> Path:
        for owner in (self.runtime_core, self.live):
            if owner is None:
                continue
            for name in (
                "project_root",
                "workspace_root",
                "repo_root",
                "root_path",
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
    def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                EvolutionPanel._deep_merge(target[key], value)
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

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def connect_events(self) -> None:
        if not self.runtime_core:
            return

        buses = [
            getattr(self.runtime_core, name, None)
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

        for bus in buses:
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
                            self._event_handler(topic),
                        )
                        if callable(unsubscribe):
                            self._event_unsubscribers.append(unsubscribe)
                    except Exception:
                        continue
                return

    def _event_handler(self, topic: str) -> Callable[[Any], None]:
        def handler(event_data: Any) -> None:
            if isinstance(event_data, dict):
                payload = event_data.get("payload", event_data)
            else:
                payload = getattr(event_data, "payload", event_data)

            if not isinstance(payload, dict):
                payload = {"detail": payload}

            self._handle_learning_event(topic, payload)

        return handler

    def _handle_learning_event(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> None:
        if topic == "level.progressed":
            self.handle_level_up_log(payload)
        elif topic in {"experience.recorded", "learning.recorded"}:
            self.handle_xp_log(payload)
        else:
            detail = (
                payload.get("message")
                or payload.get("summary")
                or payload.get("action")
                or payload.get("target_rel_path")
                or payload.get("detail")
                or ""
            )
            label = topic.replace(".", " ").title()
            self._add_timeline_entry(
                f"{label}: {detail}" if detail else label
            )

        QTimer.singleShot(100, self.refresh_snapshot)

    @Slot(dict)
    def refresh_identity_telemetry(
        self,
        identity_data: dict[str, Any],
    ) -> None:
        self.level_card.update_data(identity_data)
        self.drive_card.update_data(
            identity_data.get("drives_matrix", {})
        )
        self.skills_card.update_data(identity_data)

    def _add_timeline_entry(self, text: str) -> None:
        timestamp = QTime.currentTime().toString("hh:mm:ss")
        self.timeline_log.addItem(f"{timestamp}  {text}")
        self.timeline_log.scrollToBottom()

        while self.timeline_log.count() > 500:
            self.timeline_log.takeItem(0)

    def timeline_log_clear(self) -> None:
        self.timeline_log.clear()
        self._add_timeline_entry("Evolution event log cleared.")

    @Slot(dict)
    def handle_xp_log(self, payload: dict[str, Any]) -> None:
        action = str(
            payload.get("action_type")
            or payload.get("action")
            or "operation"
        ).replace("_", " ").title()
        xp = int(self._number(payload.get("xp_gained", 0)))
        xp_text = f"+{xp} XP" if xp >= 0 else f"{xp} XP"
        self._add_timeline_entry(f"{xp_text:<10} {action} completed")

    @Slot(dict)
    def handle_level_up_log(self, payload: dict[str, Any]) -> None:
        level = int(self._number(payload.get("level", 1)))
        rank = payload.get("permission_rank") or self._rank_for_level(level)
        self._add_timeline_entry(
            f"{'Level Up':<10} Promoted to {rank} (Lv. {level})"
        )

    def closeEvent(self, event) -> None:
        self.refresh_timer.stop()
        for unsubscribe in self._event_unsubscribers:
            try:
                unsubscribe()
            except Exception:
                pass
        self._event_unsubscribers.clear()
        super().closeEvent(event)
