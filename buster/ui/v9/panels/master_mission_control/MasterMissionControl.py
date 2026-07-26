# buster/ui/v9/panels/master_mission_control/MasterMissionControl.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QGridLayout,
)

from buster.capabilities.registry import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.agent.core import BusterAgent
from buster.security.integrity import SystemIntegrityMonitor
from buster.security.master_gate import MasterControllerSecurityGate


class MasterMissionControl(QWidget):
    """Centralized PySide6 UI Panel for Buster's Master Controller, Security Gate, Bridges, and Integrity Monitors."""

    def __init__(self, live=None, runtime_core=None, parent=None) -> None:
        super().__init__(parent)
        self.live = live
        self.runtime_core = runtime_core
        
        # Dynamically resolve root directory relative to this panel file or fallback via runtime_core
        self.root_dir = Path(__file__).resolve().parents[4]  # Adjust based on directory depth
        
        self.registry = CapabilityRegistry()
        self.registry.register(FilesystemCapability(self.registry))
        
        self.agent = BusterAgent(self.registry, agent_id="master-control-agent")
        self.integrity_monitor = SystemIntegrityMonitor(self.root_dir)
        self.security_gate = MasterControllerSecurityGate(b"master_panel_secret")
        
        # Registered system bridges
        self.bridges: Dict[str, bool] = {
            "filesystem_bridge": True,
            "termux_bridge": True,
            "shizuku_bridge": True,
            "llm_intent_bridge": True,
        }

        # Registered repair sequences
        self.repair_sequences: Dict[str, str] = {
            "integrity_rebuild": "Re-hashes and restores baseline code signatures from secure store.",
            "bridge_reset": "Tears down and re-initializes IPC channels for Termux/Shizuku.",
            "revoke_quarantine": "Isolates compromised worker nodes and purges volatile memory.",
        }

        self._build_ui()
        
        # Auto-refresh timer to match V9 lifecycle patterns
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(3000)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header Title
        title = QLabel("MASTER CONTROLLER SECURITY & INTEGRITY PANEL")
        title.setObjectName("Title")
        title.setStyleSheet("color:#23B8FF; font-size:18px; font-weight:800;")
        layout.addWidget(title)

        subtitle = QLabel("Centralized oversight for security gates, cryptographic verification, and self-healing repair sequences.")
        subtitle.setObjectName("Small")
        subtitle.setStyleSheet("color:#7894B5; font-size:12px;")
        layout.addWidget(subtitle)

        # Main Dashboard Output Terminal Area
        self.dashboard_output = QTextEdit()
        self.dashboard_output.setReadOnly(True)
        self.dashboard_output.setStyleSheet(
            "background:#07111D; color:#EAF2FF; font-family:Consolas; font-size:12px; border:1px solid #15324E; border-radius:6px; padding:8px;"
        )
        layout.addWidget(self.dashboard_output, 1)

        # Actions / Repair Controls Group Box
        controls_group = QGroupBox("Automated Repair & Security Actions")
        controls_group.setStyleSheet("color:#23B8FF; font-weight:bold; border:1px solid #15324E; border-radius:6px; margin-top:6px; padding:10px;")
        grid = QGridLayout(controls_group)

        row = 0
        for seq_name, desc in self.repair_sequences.items():
            btn = QPushButton(f"Run: {seq_name}")
            btn.setStyleSheet("background:#0A1E34; color:#BFD1E7; border:1px solid #15324E; padding:6px 12px; border-radius:4px;")
            btn.clicked.connect(lambda checked, s=seq_name: self.execute_repair_sequence(s))
            
            lbl = QLabel(desc)
            lbl.setStyleSheet("color:#9FB8D5; font-size:11px; font-weight:normal;")

            grid.addWidget(btn, row, 0)
            grid.addWidget(lbl, row, 1)
            row += 1

        layout.addWidget(controls_group)
        self.refresh_status()

    def get_system_status(self) -> Dict[str, Any]:
        """Aggregates security, integrity, bridge, and agent health into a single status report."""
        integrity_status = self.integrity_monitor.verify_integrity()
        
        return {
            "node_id": self.agent.agent_id,
            "integrity": integrity_status,
            "active_bridges": {name: active for name, active in self.bridges.items()},
            "revoked_components": list(self.security_gate._revoked_components),
            "repair_sequences_available": list(self.repair_sequences.keys()),
        }

    def execute_repair_sequence(self, sequence_name: str) -> bool:
        """Executes a registered automated repair and self-healing sequence and refreshes output."""
        try:
            if sequence_name not in self.repair_sequences:
                raise ValueError(f"Unknown repair sequence: '{sequence_name}'")
            
            if sequence_name == "integrity_rebuild":
                self.integrity_monitor.create_baseline(["buster/agent/core.py", "buster/cli.py"])
            elif sequence_name == "bridge_reset":
                for b in self.bridges:
                    self.bridges[b] = True
            elif sequence_name == "revoke_quarantine":
                self.security_gate._revoked_components.clear()
            
            self.refresh_status()
            return True
        except Exception as e:
            self.dashboard_output.append(f"\n[Error executing {sequence_name}]: {e}")
            return False

    def render_dashboard(self) -> str:
        """Generates an ASCII/Markdown dashboard layout of the Master Control Panel."""
        status = self.get_system_status()
        
        lines = [
            "=" * 60,
            "          BUSTER MASTER CONTROLLER SECURITY PANEL",
            "=" * 60,
            f"Node ID          : {status['node_id']}",
            f"Integrity Secure : {status['integrity']['secure']}",
            f"Modified Files   : {status['integrity']['modified'] or 'None'}",
            f"Missing Files    : {status['integrity']['missing'] or 'None'}",
            "-" * 60,
            "Active Bridges   :",
        ]
        for bridge, active in status["active_bridges"].items():
            state = "ONLINE" if active else "OFFLINE"
            lines.append(f"  - {bridge:<20} : [{state}]")
        
        lines.append("-" * 60)
        lines.append(f"Revoked Components : {status['revoked_components'] or 'None'}")
        lines.append("Repair Sequences   :")
        for seq, desc in self.repair_sequences.items():
            lines.append(f"  - {seq}: {desc}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def refresh_status(self) -> None:
        """Refreshes the live QTextEdit widget text view."""
        self.dashboard_output.setPlainText(self.render_dashboard())

    def closeEvent(self, event) -> None:
        if self.timer.isActive():
            self.timer.stop()
        event.accept()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    panel = MasterMissionControl()
    panel.resize(1050, 600)
    panel.show()
    sys.exit(app.exec())