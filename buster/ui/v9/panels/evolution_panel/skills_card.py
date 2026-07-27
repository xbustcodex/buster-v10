# buster/ui/v9/panels/evolution_panel/skills_card.py
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class SkillsCard(QWidget):
    """Dynamic learned skills and autonomous agent experience."""

    DEFAULT_SKILLS = (
        "Coding",
        "Python",
        "PySide6",
        "Git",
        "Repair",
        "Testing",
        "Architecture",
        "Automation",
        "RAG",
        "Planning",
        "Verification",
        "Self Improvement",
    )

    DEFAULT_AGENTS = (
        "Builder Agent",
        "Tester Agent",
        "Fixer Agent",
        "Reviewer Agent",
        "Verifier Agent",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.skill_rows: dict[str, tuple[QProgressBar, QLabel]] = {}
        self.agent_labels: dict[str, QLabel] = {}
        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 14, 15, 15)
        main_layout.setSpacing(9)

        skill_title = QLabel("LEARNED SKILL COMPETENCIES")
        skill_title.setStyleSheet(
            "font-weight:900;color:#FFB000;font-size:13px;"
            "letter-spacing:1px;background:transparent;"
        )
        main_layout.addWidget(skill_title)

        self.skills_grid = QGridLayout()
        self.skills_grid.setHorizontalSpacing(10)
        self.skills_grid.setVerticalSpacing(7)

        for skill in self.DEFAULT_SKILLS:
            self._add_skill_row(skill)

        self.skills_grid.setColumnStretch(1, 1)
        self.skills_grid.setColumnStretch(4, 1)
        main_layout.addLayout(self.skills_grid)

        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet(
            "background:#244560;margin:8px 0;"
        )
        main_layout.addWidget(separator)

        agent_title = QLabel("AGENT TEAM EXPERIENCE")
        agent_title.setStyleSheet(
            "font-weight:900;color:#31D158;font-size:13px;"
            "letter-spacing:1px;background:transparent;"
        )
        main_layout.addWidget(agent_title)

        self.agent_layout = QVBoxLayout()
        self.agent_layout.setSpacing(5)

        for agent in self.DEFAULT_AGENTS:
            self._add_agent_row(agent)

        main_layout.addLayout(self.agent_layout)

        self.learning_summary = QLabel(
            "Waiting for learning memory, pattern, strategy and outcome data."
        )
        self.learning_summary.setWordWrap(True)
        self.learning_summary.setStyleSheet(
            "color:#7894B5;font-size:10px;border-top:1px solid #244560;"
            "padding-top:8px;background:transparent;"
        )
        main_layout.addWidget(self.learning_summary)

    def _add_skill_row(self, skill: str) -> None:
        index = len(self.skill_rows)
        row = index // 2
        offset = 0 if index % 2 == 0 else 3

        name_label = QLabel(skill)
        name_label.setMinimumWidth(92)
        name_label.setStyleSheet(
            "color:#C7D8EA;font-size:10px;background:transparent;"
        )

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(11)
        bar.setStyleSheet(
            """
            QProgressBar {
                background:#081522;
                border:1px solid #244560;
                border-radius:3px;
            }
            QProgressBar::chunk {
                background:#FFB000;
                border-radius:2px;
            }
            """
        )

        value_label = QLabel("0%")
        value_label.setMinimumWidth(35)
        value_label.setStyleSheet(
            "color:#EAF2FF;font-size:10px;font-weight:800;"
            "background:transparent;"
        )

        self.skills_grid.addWidget(name_label, row, offset)
        self.skills_grid.addWidget(bar, row, offset + 1)
        self.skills_grid.addWidget(value_label, row, offset + 2)
        self.skill_rows[skill] = (bar, value_label)

    def _add_agent_row(self, agent: str) -> None:
        row = QHBoxLayout()

        name_label = QLabel(agent)
        name_label.setStyleSheet(
            "color:#C7D8EA;font-size:11px;background:transparent;"
        )

        status_label = QLabel(
            "Level 1 · 0 tasks · 0.0% success"
        )
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_label.setStyleSheet(
            "color:#9EB6CF;font-size:10px;background:transparent;"
        )

        row.addWidget(name_label)
        row.addStretch()
        row.addWidget(status_label)
        self.agent_layout.addLayout(row)
        self.agent_labels[agent] = status_label

    def update_data(self, ctx: dict[str, Any]) -> None:
        tree = ctx.get("skills_tree", {}) or {}

        for skill_name in tree:
            if skill_name not in self.skill_rows:
                self._add_skill_row(str(skill_name))

        for skill_name, (bar, label) in self.skill_rows.items():
            raw = tree.get(skill_name, 0)
            if isinstance(raw, dict):
                raw = (
                    raw.get("percent")
                    or raw.get("score")
                    or raw.get("level")
                    or 0
                )

            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0

            if 0 <= value <= 1:
                value *= 100

            value = int(max(0, min(100, value)))
            bar.setValue(value)
            label.setText(f"{value}%")

        agents_data = ctx.get("agents", {}) or {}
        for agent_name in agents_data:
            if agent_name not in self.agent_labels:
                self._add_agent_row(str(agent_name))

        for agent_name, label in self.agent_labels.items():
            data = agents_data.get(agent_name, {})
            if not isinstance(data, dict):
                continue

            level = int(data.get("level", 1) or 1)
            success = float(
                data.get("success_rate")
                or data.get("success")
                or 0
            )
            tasks = int(
                data.get("tasks")
                or data.get("completed")
                or data.get("task_count")
                or 0
            )
            label.setText(
                f"Level {level} · {tasks} tasks · {success:.1f}% success"
            )

        metrics = ctx.get("learning_metrics", {}) or {}
        self.learning_summary.setText(
            "Learning memory: "
            f"{int(metrics.get('lessons', 0) or 0)} lessons · "
            f"{int(metrics.get('patterns', 0) or 0)} patterns · "
            f"{int(metrics.get('strategies', 0) or 0)} strategies · "
            f"{int(metrics.get('verified_successes', 0) or 0)} verified "
            "successful outcomes"
        )
