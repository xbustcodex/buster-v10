# tests/test_v25_3_task_bridge.py
import asyncio
import pytest
from buster.node.task_bridge import WebSocketTaskBridge, TaskPayload


@pytest.mark.asyncio
async def test_websocket_task_bridge_streaming():
    bridge = WebSocketTaskBridge(node_id="buster_windows_host")
    
    events = []
    def on_task_update(task: TaskPayload):
        events.append((task.status, task.output))

    bridge.subscribe(on_task_update)

    task = bridge.create_task(
        task_id="task_001",
        command="python3 mobile_diagnostics.py",
        target_node="buster_pixel_6a",
    )

    assert task.status == "pending"

    completed_task = await bridge.execute_task_stream(
        task_id="task_001",
        mock_output_chunks=["Initializing Shizuku...", "Running diagnostics...", "All systems nominal."],
    )

    assert completed_task.status == "completed"
    assert "All systems nominal." in completed_task.output
    assert len(events) >= 3