# tests/test_v27_sync_engine.py
import pytest
from buster.node.communication_center import BusterCommunicationCenter
from buster.node.sync_engine import CollaborativeSyncEngine


def test_collaborative_sync_engine(tmp_path):
    registry = tmp_path / "mesh_registry.json"
    patches_dir = tmp_path / "synced_patches"
    
    comm_center = BusterCommunicationCenter(registry_path=registry)

    # Register two nodes: desktop and mobile
    comm_center.register_node("desktop_node", "desktop", "127.0.0.1:8000")
    comm_center.register_node("mobile_node", "pixel_6a_mobile", "termux://local")

    # Instantiate sync engines for both nodes
    desktop_sync = CollaborativeSyncEngine("desktop_node", comm_center, local_patches_dir=patches_dir / "desktop")
    mobile_sync = CollaborativeSyncEngine("mobile_node", comm_center, local_patches_dir=patches_dir / "mobile")

    # Desktop publishes a verified tool patch / optimization
    desktop_sync.publish_knowledge(
        knowledge_type="tool_patch",
        content={"script": "os_optimizer.py", "improvement": "Reduced latency by 15%"},
        recipient_id="mobile_node",
    )

    # Mobile node checks for incoming sync packets and integrates them
    synced_packets = mobile_sync.process_incoming_syncs()

    assert len(synced_packets) == 1
    packet = synced_packets[0]
    assert packet.source_node == "desktop_node"
    assert packet.knowledge_type == "tool_patch"
    assert packet.content["improvement"] == "Reduced latency by 15%"

    # Verify patch file was saved locally for the mobile node
    saved_files = list((patches_dir / "mobile").glob("*.json"))
    assert len(saved_files) == 1