from pathlib import Path

Path("buster/ai_state").mkdir(parents=True, exist_ok=True)
Path("buster/ai_state/__init__.py").write_text("", encoding="utf-8")

Path("buster/ai_state/state.py").write_text(r'''
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
''', encoding="utf-8")

# Patch BrainEngine
engine = Path("buster/brain/engine.py")
text = engine.read_text(encoding="utf-8")

if "from buster.ai_state.state import AIStateStore" not in text:
    text = text.replace(
        "from buster.workspace.runtime import WorkspaceSnapshot\n",
        "from buster.workspace.runtime import WorkspaceSnapshot\nfrom buster.ai_state.state import AIStateStore\n",
    )

if 'if cmd in ["ai os state", "buster state", "brain state"]:' not in text:
    text = text.replace(
        "        cmd = text.strip().lower()\n",
        '''        cmd = text.strip().lower()
        AIStateStore().update(mode="thinking", last_command=text)

        if cmd in ["ai os state", "buster state", "brain state"]:
            return AIStateStore().report()

''',
        1,
    )

# Patch normal return path to remember last response
text = text.replace(
    "        self.services.get(\"conversation\").add_assistant(reply)\n        return reply",
    '''        self.services.get("conversation").add_assistant(reply)
        AIStateStore().update(mode="idle", last_response=reply)
        return reply''',
    1,
)

engine.write_text(text, encoding="utf-8")

Path("tests/test_v9_ai_os_state.py").write_text(r'''
from buster.ai_state.state import AIStateStore

def test_ai_state_report():
    store = AIStateStore(path="data/test_ai_os_state.json")
    store.update(mode="testing", current_project="buster")
    report = store.report()
    assert "Buster AI OS State" in report
    assert "testing" in report
''', encoding="utf-8")

print("v9 AI OS State installed.")