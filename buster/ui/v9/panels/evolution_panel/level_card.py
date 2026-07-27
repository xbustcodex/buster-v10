# buster/ui/v9/panels/evolution_panel/level_card.py
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class LevelCard(QWidget):
    """Identity, experience, trust and unlock telemetry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 15)
        layout.setSpacing(9)

        self.title_label = QLabel("EVOLUTION IDENTITY")
        self.title_label.setStyleSheet(
            "font-weight:900;font-size:13px;color:#23B8FF;"
            "letter-spacing:1px;background:transparent;"
        )
        layout.addWidget(self.title_label)

        top = QHBoxLayout()
        self.tier_label = QLabel("Level 1 — Operator")
        self.tier_label.setStyleSheet(
            "font-size:17px;font-weight:900;color:#EAF2FF;"
            "background:transparent;"
        )
        top.addWidget(self.tier_label)
        top.addStretch()

        self.rank_label = QLabel("OPERATOR")
        self.rank_label.setStyleSheet(
            "background:#17334E;color:#23B8FF;border:1px solid #2878B8;"
            "border-radius:6px;padding:4px 9px;font-size:10px;"
            "font-weight:800;"
        )
        top.addWidget(self.rank_label)
        layout.addLayout(top)

        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 100)
        self.xp_bar.setValue(0)
        self.xp_bar.setFormat("0 / 100 XP")
        self.xp_bar.setFixedHeight(21)
        self.xp_bar.setStyleSheet(
            """
            QProgressBar {
                background:#081522;
                color:#EAF2FF;
                border:1px solid #244560;
                border-radius:5px;
                text-align:center;
                font-size:10px;
                font-weight:800;
            }
            QProgressBar::chunk {
                background:#23B8FF;
                border-radius:4px;
            }
            """
        )
        layout.addWidget(self.xp_bar)

        stats = QGridLayout()
        stats.setHorizontalSpacing(14)
        stats.setVerticalSpacing(5)

        self.trust_label = QLabel("0%")
        self.success_label = QLabel("0%")
        self.patterns_label = QLabel("0")
        self.strategies_label = QLabel("0")
        self.lessons_label = QLabel("0")
        self.verified_label = QLabel("0")

        entries = (
            ("Capability trust", self.trust_label),
            ("Verified success", self.success_label),
            ("Learned patterns", self.patterns_label),
            ("Build strategies", self.strategies_label),
            ("Experience lessons", self.lessons_label),
            ("Verified outcomes", self.verified_label),
        )

        for index, (name, value_label) in enumerate(entries):
            row = index // 3
            column = (index % 3) * 2

            name_label = QLabel(name)
            name_label.setStyleSheet(
                "color:#8FA9C4;font-size:10px;background:transparent;"
            )
            value_label.setStyleSheet(
                "color:#EAF2FF;font-size:12px;font-weight:800;"
                "background:transparent;"
            )

            stats.addWidget(name_label, row * 2, column)
            stats.addWidget(value_label, row * 2 + 1, column)

        layout.addLayout(stats)

        self.permissions_label = QLabel(
            "Current access: awaiting capability state"
        )
        self.permissions_label.setWordWrap(True)
        self.permissions_label.setStyleSheet(
            "color:#AFC8E6;font-size:11px;background:transparent;"
        )
        layout.addWidget(self.permissions_label)

        self.unlock_card = QLabel(
            "Next unlock: accumulate verified successful work."
        )
        self.unlock_card.setWordWrap(True)
        self.unlock_card.setStyleSheet(
            "color:#FFB000;font-size:11px;font-style:italic;"
            "border-top:1px solid #244560;padding-top:8px;"
            "background:transparent;"
        )
        layout.addWidget(self.unlock_card)

    def update_data(self, ctx: dict[str, Any]) -> None:
        level = int(ctx.get("level", 1) or 1)
        rank = str(
            ctx.get("permission_rank")
            or ctx.get("rank")
            or "Operator"
        )
        title = str(ctx.get("title") or f"Level {level} — {rank}")

        xp = int(ctx.get("xp", 0) or 0)
        xp_next = int(ctx.get("xp_next", 100) or 100)
        xp_pct = int(ctx.get("xp_pct", 0) or 0)

        self.tier_label.setText(title)
        self.rank_label.setText(rank.upper())
        self.xp_bar.setValue(max(0, min(100, xp_pct)))
        self.xp_bar.setFormat(f"{xp:,} / {xp_next:,} XP")

        trust = ctx.get("trust", 0)
        if isinstance(trust, str):
            trust_text = trust if trust.endswith("%") else f"{trust}%"
        else:
            trust_text = f"{float(trust or 0):.1f}%"
        self.trust_label.setText(trust_text)

        metrics = ctx.get("learning_metrics", {}) or {}
        self.success_label.setText(
            f"{float(metrics.get('success_rate', 0) or 0):.1f}%"
        )
        self.patterns_label.setText(
            str(int(metrics.get("patterns", 0) or 0))
        )
        self.strategies_label.setText(
            str(int(metrics.get("strategies", 0) or 0))
        )
        self.lessons_label.setText(
            str(int(metrics.get("lessons", 0) or 0))
        )
        self.verified_label.setText(
            str(int(metrics.get("verified_successes", 0) or 0))
        )

        permissions = ctx.get("permissions", []) or []
        if isinstance(permissions, str):
            permission_text = permissions
        else:
            permission_text = ", ".join(str(item) for item in permissions)

        if not permission_text:
            permission_text = self._default_permissions(level)

        self.permissions_label.setText(
            f"Current access: {permission_text}"
        )
        self.unlock_card.setText(
            "Next unlock: "
            + str(
                ctx.get("next_unlock")
                or self._default_unlock(level)
            )
        )

    @staticmethod
    def _default_permissions(level: int) -> str:
        if level >= 9:
            return (
                "verified autonomous repair loops, strategy reuse, "
                "transactional deployment with policy gates"
            )
        if level >= 6:
            return (
                "Git commits, automated refactoring, verification loops, "
                "pattern and strategy recommendations"
            )
        if level >= 3:
            return (
                "approved file changes, local execution, testing and "
                "guided repair planning"
            )
        return "read-only diagnostics and user-approved file adjustments"

    @staticmethod
    def _default_unlock(level: int) -> str:
        if level >= 9:
            return "Systems Architect after sustained safe autonomy outcomes."
        if level >= 6:
            return "Autonomy Engineer after policy and security review."
        if level >= 3:
            return "Senior Builder after verified repair consistency."
        return "Developer after successful reviewed code evaluations."
