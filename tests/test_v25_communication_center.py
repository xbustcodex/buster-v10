# tests/test_v25_communication_center.py
import pytest
from buster.node.communication_center import BusterCommunicationCenter


def test_communication_center_node_registration_and_messaging(tmp_path):
    registry = tmp_path / "mesh_registry.json"
    center = BusterCommunicationCenter(registry_path=registry)

    # Register Desktop Node
    desktop = center.register_node(
        node_id="buster_desktop_01",
        node_type="desktop",
        endpoint_address="127.0.0.1:8000",
        capabilities=["vision", "execution", "strategic_planner"],
    )
    assert desktop.node_id == "buster_desktop_01"

    # Register Mobile Pixel 6a Node
    mobile = center.register_node(
        node_id="buster_pixel_6a",
        node_type="pixel_6a_mobile",
        endpoint_address="termux://local",
        capabilities=["sensors", "termux_wrapper", "shizuku"],
    )
    assert mobile.node_type == "pixel_6a_mobile"

    # Send a shared learning/preference message from desktop to mobile
    msg = center.send_message(
        sender_id="buster_desktop_01",
        recipient_id="buster_pixel_6a",
        message_type="share_preference",
        payload={"learned_interest": "pork steaks & python automation", "affinity_score": 0.95},
    )

    assert msg.sender_id == "buster_desktop_01"
    assert msg.recipient_id == "buster_pixel_6a"

    # Fetch messages for mobile node
    inbox = center.get_messages_for("buster_pixel_6a")
    assert len(inbox) == 1
    assert inbox[0].payload["affinity_score"] == 0.95

    # Check inbox is cleared after retrieval
    assert len(center.get_messages_for("buster_pixel_6a")) == 0