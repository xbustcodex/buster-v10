from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.sdk import BusterSDK


class V6FoundationRuntime:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.sdk = BusterSDK(data_dir=data_dir)
        self.running = False

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.sdk.publish("runtime.v6.start", {"running": True}, source="v6_foundation")
        return {"running": True, "sdk": self.sdk.status()}

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.sdk.publish("runtime.v6.stop", {"running": False}, source="v6_foundation")
        return {"running": False, "sdk": self.sdk.status()}

    def status(self) -> Dict[str, Any]:
        return {"running": self.running, "sdk": self.sdk.status()}
