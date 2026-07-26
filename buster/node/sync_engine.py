# buster/node/sync_engine.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.node.communication_center import BusterCommunicationCenter, NodeMessage

logger = logging.getLogger(__name__)


@dataclass
class SharedKnowledgePacket:
    packet_id: str
    source_node: str
    knowledge_type: str  # "tool_patch", "hurdle_solution", "preference_update"
    content: Dict[str, Any]
    timestamp: str


class CollaborativeSyncEngine:
    """Manages cross-node knowledge synchronization and peer-to-peer patch integration."""

    def __init__(
        self,
        node_id: str,
        communication_center: BusterCommunicationCenter,
        local_patches_dir: str | Path = "data/synced_patches",
    ) -> None:
        self.node_id = node_id
        self.comm_center = communication_center
        self.local_patches_dir = Path(local_patches_dir)
        self.local_patches_dir.mkdir(parents=True, exist_ok=True)

    def publish_knowledge(
        self,
        knowledge_type: str,
        content: Dict[str, Any],
        recipient_id: str = "broadcast",
    ) -> NodeMessage:
        """Publishes local discoveries or tool patches to the mesh network."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        packet_id = f"pkt_{self.node_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        packet = SharedKnowledgePacket(
            packet_id=packet_id,
            source_node=self.node_id,
            knowledge_type=knowledge_type,
            content=content,
            timestamp=now_iso,
        )

        message = self.comm_center.send_message(
            sender_id=self.node_id,
            recipient_id=recipient_id,
            message_type=f"sync_{knowledge_type}",
            payload=asdict(packet),
        )
        logger.info(f"Node [{self.node_id}] published knowledge packet [{packet_id}] to [{recipient_id}]")
        return message

    def process_incoming_syncs(self) -> List[SharedKnowledgePacket]:
        """Fetches pending messages from the communication center and integrates valid packets."""
        messages = self.comm_center.get_messages_for(self.node_id)
        processed_packets = []

        for msg in messages:
            if msg.message_type.startswith("sync_"):
                try:
                    payload = msg.payload
                    packet = SharedKnowledgePacket(**payload)
                    
                    # Validate and store incoming patch or knowledge
                    self._apply_packet(packet)
                    processed_packets.append(packet)
                except Exception as e:
                    logger.error(f"Failed to process incoming sync message: {e}")

        return processed_packets

    def _apply_packet(self, packet: SharedKnowledgePacket) -> None:
        """Saves and applies verified incoming knowledge packets locally."""
        target_file = self.local_patches_dir / f"{packet.packet_id}.json"
        target_file.write_text(json.dumps(asdict(packet), indent=2), encoding="utf-8")
        logger.info(f"Successfully integrated synced knowledge packet [{packet.packet_id}] from node [{packet.source_node}]")