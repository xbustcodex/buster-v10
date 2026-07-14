
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path

@dataclass
class BusterAIState:
    mode: str = "idle"
    current_project: str = ""
    current_folder: str = ""
    git_branch: str = ""
    git_status: str = ""
    ai_provider: str = "unknown"
    voice_status: str = "standby"
    vision_status: str = "standby"
    last_command: str = ""
    last_response: str = ""
    last_updated: str = ""

class AIStateStore:
    def __init__(self, path="data/ai_os_state.json"):
        self.path = Path(path)
        self.state = BusterAIState()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        self.state.last_updated = datetime.now().isoformat(timespec="seconds")
        self.save()
        return self.state

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(self.state), indent=2), encoding="utf-8")

    def load(self):
        if not self.path.exists():
            self.save()
            return self.state

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.state = BusterAIState(**{**asdict(BusterAIState()), **data})
        except Exception:
            pass

        return self.state

    def report(self):
        s = self.load()
        return (
            "Buster AI OS State\n"
            f"Mode: {s.mode}\n"
            f"Project: {s.current_project}\n"
            f"Folder: {s.current_folder}\n"
            f"Git: {s.git_branch} / {s.git_status}\n"
            f"AI Provider: {s.ai_provider}\n"
            f"Voice: {s.voice_status}\n"
            f"Vision: {s.vision_status}\n"
            f"Last command: {s.last_command}\n"
            f"Last updated: {s.last_updated}"
        )
