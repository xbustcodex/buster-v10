#!/usr/bin/env python3
"""
agent.py - Agent Collaboration & OS Dashboard Panel using PySide6
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# ==================== Data Models ====================

@dataclass
class Agent:
    """Agent data model"""
    id: str
    name: str
    role: str
    status: str  # idle, working, thinking, speaking
    face_expression: str
    current_task: Optional[str] = None
    priority: int = 0
    last_active: Optional[str] = None
    
@dataclass
class ConversationMessage:
    """Conversation message model"""
    speaker: str
    message: str
    timestamp: str
    agent_id: Optional[str] = None
    
@dataclass
class Activity:
    """Activity log entry"""
    agent: str
    action: str
    timestamp: str
    details: Optional[str] = None

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"

# ==================== Agent Dashboard Model ====================

class AgentDashboardModel(QObject):
    """Model for the agent dashboard data"""
    
    dataChanged = Signal()
    
    def __init__(self, data_dir: str | Path = "data"):
        super().__init__()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize with default data
        self.agents: List[Agent] = []
        self.conversation: List[ConversationMessage] = []
        self.activities: List[Activity] = []
        self.voice_queue: List[str] = []
        self.title = "Agent Runtime & Living Companion"
        self.face_expression = "idle"
        
        # Load or create initial agents
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize default agents"""
        default_agents = [

            Agent(
                id="planner",
                name="Planner",
                role="Planning Agent",
                status="idle",
                face_expression="thinking",
                priority=1,
            ),

            Agent(
                id="builder",
                name="Builder",
                role="Build Agent",
                status="idle",
                face_expression="happy",
                priority=2,
            ),

            Agent(
                id="tester",
                name="Tester",
                role="Testing Agent",
                status="idle",
                face_expression="neutral",
                priority=3,
            ),

            Agent(
                id="reviewer",
                name="Reviewer",
                role="Code Review",
                status="idle",
                face_expression="curious",
                priority=4,
            ),

            Agent(
                id="fixer",
                name="Fixer",
                role="Repair Agent",
                status="idle",
                face_expression="thinking",
                priority=5,
            ),
        ]
        self.agents = default_agents
        
        # Add initial conversation
        self.conversation = [
            ConversationMessage(
                "System",
                "Agent system initialized",
                datetime.now().isoformat()
            ),
            ConversationMessage(
                "Buster",
                "Ready to collaborate! 🤝",
                datetime.now().isoformat(),
                "agent_001"
            )
        ]
        
        # Add initial activities
        self.activities = [
            Activity(
                "System",
                "Dashboard started",
                datetime.now().isoformat()
            )
        ]
        
    def snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the current state"""
        return {
            "title": self.title,
            "face_expression": self.face_expression,
            "active_agents": [asdict(a) for a in self.agents],
            "agents": [asdict(a) for a in self.agents],
            "latest_activity": [asdict(a) for a in self.activities[-10:]],
            "agent_conversation": [asdict(m) for m in self.conversation[-20:]],
            "pending_voice": self.voice_queue,
            "messages": [asdict(m) for m in self.conversation],
            "timeline": [asdict(a) for a in self.activities]
        }
    
    def add_agent(self, name: str, role: str) -> None:
        """Add a new agent"""
        agent_id = f"agent_{len(self.agents)+1:03d}"
        agent = Agent(
            id=agent_id,
            name=name,
            role=role,
            status="idle",
            face_expression="neutral",
            priority=len(self.agents) + 1
        )
        self.agents.append(agent)
        self.add_activity("System", f"Added agent: {name}")
        self.dataChanged.emit()
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent"""
        self.agents = [a for a in self.agents if a.id != agent_id]
        self.add_activity("System", f"Removed agent: {agent_id}")
        self.dataChanged.emit()
    
    def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update an agent's status"""
        for agent in self.agents:
            if agent.id == agent_id:
                agent.status = status
                agent.last_active = datetime.now().isoformat()
                self.dataChanged.emit()
                break
    
    def add_conversation(self, speaker: str, message: str, agent_id: Optional[str] = None) -> None:
        """Add a conversation message"""
        msg = ConversationMessage(
            speaker=speaker,
            message=message,
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id
        )
        self.conversation.append(msg)
        self.dataChanged.emit()
    
    def add_activity(self, agent: str, action: str, details: Optional[str] = None) -> None:
        """Add an activity log entry"""
        activity = Activity(
            agent=agent,
            action=action,
            timestamp=datetime.now().isoformat(),
            details=details
        )
        self.activities.append(activity)
        self.dataChanged.emit()

# ==================== Agent Dashboard Widget ====================

class AgentDashboardWidget(QWidget):
    """Main agent dashboard widget"""
    
    def __init__(self, data_dir: str | Path = "data", parent=None):
        super().__init__(parent)
        self.model = AgentDashboardModel(data_dir)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_agents)
        self.animation_timer.start(3000)  # Update every 3 seconds
        
        self.setup_ui()
        self.connect_signals()
        self.refresh_display()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ===== Header =====
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.title_label = QLabel("🤖 Agent Collaboration System")
        self.title_label.setStyleSheet("""
            font-size: 18pt;
            font-weight: bold;
            color: #ffffff;
        """)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("● Online")
        self.status_indicator.setStyleSheet("""
            color: #4ec9b0;
            font-weight: bold;
            font-size: 10pt;
        """)
        header_layout.addWidget(self.status_indicator)
        
        # Agent count
        self.agent_count_label = QLabel("Agents: 0")
        self.agent_count_label.setStyleSheet("""
            color: #569cd6;
            font-size: 10pt;
        """)
        header_layout.addWidget(self.agent_count_label)
        
        layout.addWidget(header_widget)
        
        # ===== Main Content =====
        content_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(content_splitter, 1)
        
        # Left panel - Agents
        left_panel = QWidget()
        left_panel.setMaximumWidth(260)
        left_panel.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Agent list header
        agent_header = QLabel("🧠 Active Agents")
        agent_header.setStyleSheet("""
            font-size: 12pt;
            font-weight: bold;
            color: #4ec9b0;
            padding: 5px 0;
        """)
        left_layout.addWidget(agent_header)
        
        # Agent list
        self.agent_list = QListWidget()
        self.agent_list.setStyleSheet("""
            QListWidget {
                background-color: #252525;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
            QListWidget::item:selected {
                background-color: #2d4a6b;
            }
        """)
        left_layout.addWidget(self.agent_list)
        
        # Agent controls
        agent_controls = QHBoxLayout()
        self.add_agent_btn = QPushButton("➕ Add Agent")
        self.add_agent_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #4ec9b0;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        agent_controls.addWidget(self.add_agent_btn)
        
        self.remove_agent_btn = QPushButton("✖ Remove Agent")
        self.remove_agent_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #f44747;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        agent_controls.addWidget(self.remove_agent_btn)
        
        left_layout.addLayout(agent_controls)
        content_splitter.addWidget(left_panel)
        
        # Right panel - Details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # ===== Conversation Tab =====
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: #252525;
                border: 1px solid #333333;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #888888;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)
        
        # Conversation tab
        conversation_tab = QWidget()
        conv_layout = QVBoxLayout(conversation_tab)
        
        self.conversation_text = QTextEdit()
        self.conversation_text.setReadOnly(True)
        self.conversation_text.setStyleSheet("""
            background-color: #1e1e1e;
            border: none;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            font-size: 10pt;
        """)
        conv_layout.addWidget(self.conversation_text)
        
        # Message input
        msg_input_widget = QWidget()
        msg_input_layout = QHBoxLayout(msg_input_widget)
        msg_input_layout.setContentsMargins(0, 5, 0, 5)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message to the agents...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #4ec9b0;
            }
        """)
        msg_input_layout.addWidget(self.message_input)
        
        self.send_btn = QPushButton("📤 Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4ec9b0;
                color: #1e1e1e;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5ed9c0;
            }
        """)
        msg_input_layout.addWidget(self.send_btn)
        
        conv_layout.addWidget(msg_input_widget)
        
        self.tab_widget.addTab(conversation_tab, "💬 Conversation")
        
        # Activity tab
        activity_tab = QWidget()
        activity_layout = QVBoxLayout(activity_tab)
        
        self.activity_text = QTextEdit()
        self.activity_text.setReadOnly(True)
        self.activity_text.setStyleSheet("""
            background-color: #1e1e1e;
            border: none;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            font-size: 9pt;
        """)
        activity_layout.addWidget(self.activity_text)
        
        self.tab_widget.addTab(activity_tab, "📋 Activity")
        
        # Voice queue tab
        voice_tab = QWidget()
        voice_layout = QVBoxLayout(voice_tab)
        
        self.voice_text = QTextEdit()
        self.voice_text.setReadOnly(True)
        self.voice_text.setStyleSheet("""
            background-color: #1e1e1e;
            border: none;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            font-size: 10pt;
        """)
        voice_layout.addWidget(self.voice_text)
        
        self.tab_widget.addTab(voice_tab, "🎙️ Voice Queue")
        
        right_layout.addWidget(self.tab_widget)
        
        # ===== Status Bar =====
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                color: #888888;
                border-top: 1px solid #333333;
                padding: 2px 5px;
            }
        """)
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)
        status_bar.addPermanentWidget(QLabel("✨ AgentOS v1.0"))
        layout.addWidget(status_bar)
        
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([220, 600])
        
        # Set initial focus
        self.message_input.setFocus()
        
    def connect_signals(self):
        """Connect signals to slots"""
        self.model.dataChanged.connect(self.refresh_display)
        self.add_agent_btn.clicked.connect(self.show_add_agent_dialog)
        self.remove_agent_btn.clicked.connect(self.remove_selected_agent)
        self.send_btn.clicked.connect(self.send_message)
        self.message_input.returnPressed.connect(self.send_message)
        
    @Slot()
    def refresh_display(self):
        """Refresh the entire display"""
        self.update_agent_list()
        self.update_conversation()
        self.update_activity()
        self.update_voice_queue()
        self.update_stats()
        
    def update_agent_list(self):
        """Update the agent list"""
        self.agent_list.clear()
        for agent in self.model.agents:
            # Create item with status indicator
            status_colors = {
                "idle": "#888888",
                "working": "#4ec9b0",
                "thinking": "#dcdcaa",
                "speaking": "#569cd6",
                "error": "#f44747"
            }
            color = status_colors.get(agent.status, "#888888")
            
            # Face emojis
            face_emojis = {
                "happy": "😊",
                "curious": "🤔",
                "thinking": "🤔",
                "neutral": "😐",
                "excited": "😃",
                "idle": "😴"
            }
            face = face_emojis.get(agent.face_expression, "🤖")
            
            item_text = f"{face} {agent.name}  ● {agent.role}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, agent.id)
            
            # Set item color based on status
            item.setForeground(QColor(color))
            
            # Add status badge
            status_text = f"  [{agent.status.upper()}]"
            if agent.current_task:
                status_text += f"  📝 {agent.current_task}"
            item.setText(item_text + status_text)
            
            self.agent_list.addItem(item)
    
    def update_conversation(self):
        """Update the conversation display"""
        self.conversation_text.clear()
        for msg in self.model.conversation[-50:]:  # Show last 50 messages
            speaker_color = "#4ec9b0" if msg.speaker in ["Buster", "Nova", "Echo", "Raven"] else "#569cd6"
            time_str = datetime.fromisoformat(msg.timestamp).strftime("%H:%M:%S")
            self.conversation_text.append(
                f'<span style="color: #888888;">[{time_str}]</span> '
                f'<span style="color: {speaker_color}; font-weight: bold;">{msg.speaker}:</span> '
                f'<span style="color: #d4d4d4;">{msg.message}</span>'
            )
        # Scroll to bottom
        scrollbar = self.conversation_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_activity(self):
        """Update the activity display"""
        self.activity_text.clear()
        for activity in self.model.activities[-50:]:  # Show last 50 activities
            time_str = datetime.fromisoformat(activity.timestamp).strftime("%H:%M:%S")
            color = "#4ec9b0" if activity.agent == "System" else "#d4d4d4"
            self.activity_text.append(
                f'<span style="color: #888888;">[{time_str}]</span> '
                f'<span style="color: #569cd6;">{activity.agent}</span> '
                f'<span style="color: {color};">{activity.action}</span>'
                f'{f" <span style=\"color: #888888;\">- {activity.details}</span>" if activity.details else ""}'
            )
        scrollbar = self.activity_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_voice_queue(self):
        """Update the voice queue display"""
        self.voice_text.clear()
        for i, voice in enumerate(self.model.voice_queue, 1):
            self.voice_text.append(
                f'<span style="color: #888888;">#{i}</span> '
                f'<span style="color: #d4d4d4;">{voice}</span>'
            )
    
    def update_stats(self):
        """Update statistics display"""
        count = len(self.model.agents)
        self.agent_count_label.setText(f"Agents: {count}")
        
        # Update status
        active_count = sum(1 for a in self.model.agents if a.status in ["working", "thinking", "speaking"])
        if active_count > 0:
            self.status_indicator.setText(f"● {active_count} active")
            self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold; font-size: 10pt;")
        else:
            self.status_indicator.setText("● Idle")
            self.status_indicator.setStyleSheet("color: #888888; font-weight: bold; font-size: 10pt;")
    
    @Slot()
    def show_add_agent_dialog(self):
        """Show dialog to add a new agent"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Agent")
        dialog.setModal(True)
        dialog.setStyleSheet(self.styleSheet())
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Name input
        name_label = QLabel("Agent Name:")
        name_label.setStyleSheet("color: #d4d4d4;")
        layout.addWidget(name_label)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter agent name...")
        layout.addWidget(name_input)
        
        # Role input
        role_label = QLabel("Role:")
        role_label.setStyleSheet("color: #d4d4d4;")
        layout.addWidget(role_label)
        
        role_input = QLineEdit()
        role_input.setPlaceholderText("Enter role...")
        layout.addWidget(role_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Agent")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4ec9b0;
                color: #1e1e1e;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5ed9c0;
            }
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def add_agent():
            name = name_input.text().strip()
            role = role_input.text().strip()
            if name and role:
                self.model.add_agent(name, role)
                dialog.accept()
                self.model.add_conversation("System", f"Agent {name} joined the team!")
            else:
                QMessageBox.warning(dialog, "Error", "Please enter both name and role")
        
        add_btn.clicked.connect(add_agent)
        cancel_btn.clicked.connect(dialog.reject)
        name_input.returnPressed.connect(add_agent)
        
        dialog.exec()
    
    @Slot()
    def remove_selected_agent(self):
        """Remove the selected agent"""
        current_item = self.agent_list.currentItem()
        if current_item:
            agent_id = current_item.data(Qt.UserRole)
            agent = next((a for a in self.model.agents if a.id == agent_id), None)
            if agent:
                reply = QMessageBox.question(
                    self,
                    "Remove Agent",
                    f"Are you sure you want to remove {agent.name}?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.model.remove_agent(agent_id)
                    self.model.add_conversation("System", f"Agent {agent.name} has left")
        else:
            QMessageBox.information(self, "Info", "Please select an agent first")
    
    @Slot()
    def send_message(self):
        """Send a message to the conversation"""
        message = self.message_input.text().strip()
        if message:
            # Add to conversation
            self.model.add_conversation("User", message)
            self.message_input.clear()
            
            # Simulate agent responses
            self.simulate_agent_response(message)
    
    def simulate_agent_response(self, user_message: str):
        """Simulate agent responses to user messages"""
        # Randomly select an active agent to respond
        if self.model.agents:
            agent = random.choice(self.model.agents)
            
            # Update agent status
            self.model.update_agent_status(agent.id, "thinking")
            
            # Simulate thinking time
            QTimer.singleShot(1000, lambda: self._generate_response(agent, user_message))
    
    def _generate_response(self, agent: Agent, user_message: str):
        """Generate a response from an agent"""
        responses = {
            "Buster": [
                "I can help with that! Let me analyze the code.",
                "Interesting! I'll take a look at this issue.",
                "Great question! I'll collaborate with the team.",
                "Let me run some tests and get back to you."
            ],
            "Nova": [
                "I'm on it! Let me process that request.",
                "Good point! I'll research this further.",
                "I'll coordinate with the other agents.",
                "Processing your request now..."
            ],
            "Echo": [
                "I'll test that right away!",
                "Quality check in progress!",
                "Let me verify that for you.",
                "I'll run the test suite."
            ],
            "Raven": [
                "Excellent design consideration!",
                "I'll architect a solution for this.",
                "Let me review the architecture.",
                "Great insight! I'll optimize this."
            ]
        }
        
        # Default responses for unknown agents
        default_responses = [
            "I'll look into that right away!",
            "Great idea! Let me work on that.",
            "Thanks for the input! I'll get on it.",
            "Interesting challenge! I'll tackle this."
        ]
        
        agent_responses = responses.get(agent.name, default_responses)
        response = random.choice(agent_responses)
        
        # Add agent response to conversation
        self.model.add_conversation(agent.name, response, agent.id)
        self.model.add_activity(agent.name, "responded to user", user_message[:50])
        
        # Update agent status
        self.model.update_agent_status(agent.id, "idle")
        
        # Simulate voice queue
        self.model.voice_queue.append(f"{agent.name}: {response}")
        if len(self.model.voice_queue) > 10:
            self.model.voice_queue.pop(0)
        
        # Update face expression
        agent.face_expression = random.choice(["happy", "curious", "thinking", "neutral", "excited"])
        self.model.dataChanged.emit()
    
    @Slot()
    def _animate_agents(self):
        """Periodically animate agent states"""
        for agent in self.model.agents:
            if agent.status == "idle" and random.random() < 0.2:
                # Randomly change face expression
                agent.face_expression = random.choice(["happy", "curious", "thinking", "neutral", "excited"])
                self.model.dataChanged.emit()
                break



# ======================================================
# Buster Integration Panel
# ======================================================

class AgentPanel(QWidget):
    """
    Agent Manager panel used inside the Buster UI.
    """

    def __init__(self, live=None, runtime_core=None):
        super().__init__()

        self.live = live

        self.setWindowTitle("Agent Manager")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.dashboard = AgentDashboardWidget("data")

        layout.addWidget(self.dashboard)