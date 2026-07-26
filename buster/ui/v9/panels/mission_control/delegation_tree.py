from __future__ import annotations

import json
import os
from typing import Optional, Any, Dict

try:
    from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QTreeWidget, QTreeWidgetItem
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object


class DelegationTreeCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Renders hierarchical task delegation trees from snapshot state or blackboard_state.json."""

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("DELEGATION TREE", parent)
        self._setup_ui()
        self.refresh_tree()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Goal / Task", "Status", "Worker"])
        self.tree_widget.setColumnWidth(0, 220)
        self.tree_widget.setColumnWidth(1, 90)
        self.tree_widget.setStyleSheet(
            """
            QTreeWidget {
                background-color: #07111D;
                border: 1px solid #15324E;
                color: #DCEBFF;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0A1D33;
                color: #23B8FF;
                font-weight: bold;
                border: none;
            }
            """
        )
        layout.addWidget(self.tree_widget)

    def _get_blackboard_path(self) -> str:
        """Finds buster/brain/blackboard_state.json relative to project root."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir = base_dir
        while current_dir and os.path.basename(current_dir) != "buster-v10":
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent
            
        return os.path.join(current_dir, "buster", "brain", "blackboard_state.json")

    def refresh_tree(self) -> None:
        """Reads blackboard_state.json directly if snapshot data isn't provided."""
        if not PYSIDE6_AVAILABLE:
            return

        blackboard_path = self._get_blackboard_path()
        if not os.path.exists(blackboard_path):
            return

        try:
            with open(blackboard_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            goal = data.get("active_goal")
            tasks = data.get("delegation_tree", [])

            self.tree_widget.clear()

            if not goal and not tasks:
                item = QTreeWidgetItem(["No active goals", "-", "-"])
                self.tree_widget.addTopLevelItem(item)
                return

            if goal:
                goal_item = QTreeWidgetItem([str(goal), "IN PROGRESS", "Buster"])
                for subtask in tasks:
                    sub_item = QTreeWidgetItem([
                        str(subtask.get("title", "Task")),
                        str(subtask.get("status", "QUEUED")),
                        str(subtask.get("worker", "Unassigned"))
                    ])
                    goal_item.addChild(sub_item)

                self.tree_widget.addTopLevelItem(goal_item)
                goal_item.setExpanded(True)
        except Exception:
            pass

    def update_tree(self, tree_data: Optional[Dict[str, Any]] = None) -> None:
        """Called by MissionControlPanel timer pulse or snapshot update."""
        if not PYSIDE6_AVAILABLE:
            return

        if not tree_data:
            self.refresh_tree()
            return

        self.tree_widget.clear()

        for goal_id, goal_info in tree_data.items():
            goal_item = QTreeWidgetItem([str(goal_id), goal_info.get("status", "ACTIVE"), "-"])
            for subtask in goal_info.get("tasks", []):
                sub_item = QTreeWidgetItem([
                    str(subtask.get("title", "Task")),
                    str(subtask.get("status", "PENDING")),
                    str(subtask.get("assigned_worker", "Unassigned"))
                ])
                goal_item.addChild(sub_item)
            
            self.tree_widget.addTopLevelItem(goal_item)
            goal_item.setExpanded(True)