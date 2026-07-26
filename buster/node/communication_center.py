# buster/node/communication_center.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BusterNodeIdentity:
    node_id: str
    node_type: str  # "desktop", "pixel_6a_mobile", "termux_node"
    endpoint_address: str
    last_seen: str
    capabilities: List[str] = field(default_factory=list)


@dataclass
class NodeMessage:
    sender_id: str
    recipient_id: str  # "broadcast" or specific node_id
    message_type: str  # "share_preference", "share_patch", "sync_state"
    payload: Dict[str, Any]
    timestamp: str


class BusterCommunicationCenter:
    """Manages P2P discovery and knowledge synchronization between distributed Buster instances."""

    def __init__(self, registry_path: str | Path = "data/mesh_network_registry.json") -> None:
        self.registry_path = Path(registry_path)
        self.nodes: Dict[str, BusterNodeIdentity] = {}
        self.message_queue: List[NodeMessage] = []
        self._load()

    def register_node(
        self,
        node_id: str,
        node_type: str,
        endpoint_address: str,
        capabilities: Optional[List[str]] = None,
    ) -> BusterNodeIdentity:
        """Registers or updates a Buster node within the mesh network."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        identity = BusterNodeIdentity(
            node_id=node_id,
            node_type=node_type,
            endpoint_address=endpoint_address,
            last_seen=now_iso,
            capabilities=capabilities or ["perception", "execution"],
        )
        self.nodes[node_id] = identity
        self._save()
        logger.info(f"Registered Buster node [{node_id}] of type [{node_type}]")
        return identity

    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: Dict[str, Any],
    ) -> NodeMessage:
        """Transmits shared knowledge, preferences, or tool patches between nodes."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        msg = NodeMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            payload=payload,
            timestamp=now_iso,
        )
        self.message_queue.append(msg)
        self._save()
        logger.info(f"Node [{sender_id}] sent [{message_type}] to [{recipient_id}]")
        return msg

    def get_messages_for(self, node_id: str) -> List[NodeMessage]:
        """Retrieves and clears pending messages destined for a specific node or broadcast."""
        matched = []
        remaining = []
        for m in self.message_queue:
            if m.recipient_id in {node_id, "broadcast"}:
                matched.append(m)
            else:
                remaining.append(m)
        self.message_queue = remaining
        self._save()
        return matched

    def _load(self) -> None:
        if not self.registry_path.exists():
            return
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            for k, v in raw.get("nodes", {}).items():
                self.nodes[k] = BusterNodeIdentity(**v)
            self.message_queue = [NodeMessage(**m) for m in raw.get("messages", [])]
        except Exception as e:
            logger.error(f"Failed to load mesh network registry: {e}")

    def _save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": {k: asdict(v) for k, v in self.nodes.items()},
            "messages": [asdict(m) for m in self.message_queue],
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")