# To give Buster the capability to control all Linux PC machines, the architecture needs to expand beyond local mobile device automation (such as Termux and Shizuku) into a robust, secure Remote Linux Agent & Control Protocol.

Here is the blueprint for building and wiring this capability into Buster:

1. Architectural Blueprint: Buster Linux Control Plane
The system will use a secure Hub-and-Spoke model where your primary Buster desktop instance acts as the Control Hub, and target Linux PCs run a lightweight background daemon (Buster Linux Agent) communicating over encrypted gRPC or REST/WebSockets with SSH-key-based authentication.

Plaintext
Buster Hub (Main Desktop OS)
   │
   ├── SSH / Cryptographic Key Manager
   ├── Linux Fleet Orchestrator
   │     │
   │     ├── Target PC 1 (Ubuntu / Debian Server)
   │     ├── Target PC 2 (Arch Linux Workstation)
   │     └── Target PC 3 (Fedora Headless Node)
2. Core Components to Build
A. The Remote Linux Agent (buster-agent)
A lightweight Python service installed on target Linux PCs that securely exposes a controlled subset of system capabilities:

Terminal Execution: Safely runs shell commands with output streaming and exit-code reporting.

Service & Package Management: Installs packages (apt, pacman, dnf), checks systemd service health, and manages background daemons.

File Operations: Uploads, downloads, edits, and backs up configuration files using transactional safety.

System Telemetry: Monitors CPU, memory, disk usage, and temperature in real-time.

B. The Fleet Manager Panel (LinuxFleetPanel)
A new UI panel in Buster (accessible via sidebar or command palette) that provides:

Node Discovery & Registration: Add machines via IP address, SSH key, and port.

Multi-Host Terminal: Broadcast commands to a single machine or an entire fleet simultaneously.

Health & Status Dashboard: Live status indicators for all connected Linux nodes.

3. Implementation: Core Linux Controller Module
Create a secure remote execution bridge on the Buster Hub side to manage connections and dispatch commands:

Python
# buster/runtime/linux_fleet_controller.py
from __future__ import annotations

import logging
import subprocess
from typing import Dict, Any, List, Optional

logger = logging.getLogger("buster.runtime.linux_fleet_controller")

class LinuxNode:
    def __init__(self, host: str, user: str, ssh_key_path: str, port: int = 22):
        self.host = host
        self.user = user
        self.ssh_key_path = ssh_key_path
        self.port = port

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Executes a remote command securely via SSH."""
        ssh_cmd = [
            "ssh",
            "-i", self.ssh_key_path,
            "-p", str(self.port),
            "-o", "StrictHostKeyChecking=no",
            f"{self.user}@{self.host}",
            command
        ]
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out."}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class LinuxFleetController:
    """Manages a registry of remote Linux PCs and routes commands through Buster."""
    
    def __init__(self):
        self.nodes: Dict[str, LinuxNode] = {}

    def register_node(self, name: str, host: str, user: str, ssh_key_path: str, port: int = 22):
        self.nodes[name] = LinuxNode(host, user, ssh_key_path, port)
        logger.info(f"Registered Linux node: {name} ({user}@{host}:{port})")

    def run_on_node(self, name: str, command: str) -> Dict[str, Any]:
        node = self.nodes.get(name)
        if not node:
            return {"success": False, "error": f"Node '{name}' not found."}
        return node.execute_command(command)
4. Natural Language Integration via Chat
To let Buster control these machines conversationally, extend the chat routing logic so commands like "Update system packages on the media server" or "Check disk space on the build node" translate directly into fleet actions:

Intent Parsing: Buster recognizes target nodes and desired actions from natural language input.

Safety Verification: High-impact commands (like rm -rf or system reboots) require explicit user approval via the existing safety gate or approval bridge before execution.

Created: 2026-07-27T14:08:49.735678

## Status

- planning

## Notes

This is an isolated AI build workspace. Files should be created here before being merged into the main project.
