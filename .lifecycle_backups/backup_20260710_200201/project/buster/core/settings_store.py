import json
import sys
from pathlib import Path

def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]

class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else app_base_dir() / "data" / "settings.json"

    def load_into(self, settings):
        if not self.path.exists():
            self.save(settings)
            return settings

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
        except Exception:
            pass

        return settings

    def save(self, settings):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for key, value in settings.__dict__.items():
            data[key] = str(value) if isinstance(value, Path) else value

        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")