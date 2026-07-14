from pathlib import Path
import json

class WorldModelStorage:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.path = self.data_dir / "world_model.json"

    def load(self):
        if not self.path.exists():
            return {"entities": [], "observations": [], "relationships": [], "timeline": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"entities": [], "observations": [], "relationships": [], "timeline": []}

    def save(self, state):
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state
