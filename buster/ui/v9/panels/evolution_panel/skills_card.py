# buster/ui/v9/panels/evolution_panel/skills_card.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout

class SkillsCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.skill_labels = {}
        self.agent_labels = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 1. Main Skill Tree
        skill_title = QLabel("LEARNED SKILL COMPETENCIES", self)
        skill_title.setStyleSheet("font-weight: bold; color: #FFBB33;")
        main_layout.addWidget(skill_title)

        skills_grid = QGridLayout()
        skills_grid.setSpacing(8)
        skills = ["Coding", "Python", "PySide6", "Git", "Hardware", "ESP32", "Automation"]
        
        for idx, skill in enumerate(skills):
            row = idx // 2
            col = (idx % 2) * 2
            
            name_lbl = QLabel(f"{skill}:", self)
            val_lbl = QLabel("0%", self)
            val_lbl.setStyleSheet("font-weight: bold; color: #FFF;")
            
            skills_grid.addWidget(name_lbl, row, col)
            skills_grid.addWidget(val_lbl, row, col + 1)
            self.skill_labels[skill] = val_lbl
            
        main_layout.addLayout(skills_grid)
        
        # Spacer boundary line
        sep = QLabel(self)
        sep.setStyleSheet("border-top: 1px solid #333; margin: 10px 0px;")
        main_layout.addWidget(sep)

        # 2. Autonomous Agent Levels
        agent_title = QLabel("AGENT TEAM EXPERIENCE", self)
        agent_title.setStyleSheet("font-weight: bold; color: #00C851;")
        main_layout.addWidget(agent_title)

        agent_layout = QVBoxLayout()
        agents = ["Builder Agent", "Tester Agent", "Fixer Agent", "Review Agent"]
        for agent in agents:
            row = QHBoxLayout()
            name_lbl = QLabel(agent, self)
            stat_lbl = QLabel("Level 1 (Success Rate: 100%)", self)
            stat_lbl.setStyleSheet("color: #AAAAAA;")
            
            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(stat_lbl)
            agent_layout.addLayout(row)
            self.agent_labels[agent] = stat_lbl
            
        main_layout.addLayout(agent_layout)

    def update_data(self, ctx: dict):
        # Bind Skill Tree Percentages
        tree = ctx.get("skills_tree", {})
        for skill_name, label in self.skill_labels.items():
            if skill_name in tree:
                label.setText(f"{tree[skill_name]}%")

        # Bind Agent Experience Metrics
        agents_data = ctx.get("agents", {})
        for agent_name, label in self.agent_labels.items():
            if agent_name in agents_data:
                a = agents_data[agent_name]
                label.setText(f"Level {a.get('level', 1)} (Success: {a.get('success_rate', 100.0)}%)")