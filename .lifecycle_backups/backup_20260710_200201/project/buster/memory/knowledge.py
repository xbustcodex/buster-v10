import json
from pathlib import Path

class KnowledgeMemory:
    def __init__(self, path="data/knowledge_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if not self.path.exists(): return {}
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception: return {}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def remember(self, text):
        raw = text.strip().strip(".")
        low = raw.lower()
        key, value = "", raw
        for prefix, fixed in [("my browser is ", "browser"), ("my ide is ", "ide"), ("i use ", ""), ("my arduino com port is ", "arduino_com_port"), ("my com port is ", "com_port")]:
            if low.startswith(prefix):
                value = raw[len(prefix):].strip()
                key = fixed or self._simple_key(value)
                break
        if not key:
            if " is " in raw:
                left, right = raw.split(" is ", 1)
                key, value = self._simple_key(left), right.strip()
            else:
                key, value = self._simple_key(raw), raw
        self.data[key] = value
        self._save()
        return f"Remembered {key}: {value}"

    def _simple_key(self, text):
        text = text.lower().strip()
        for junk in ["remember that ", "remember ", "my ", "the "]:
            text = text.replace(junk, "")
        return "_".join(text.split())[:60] or "note"

    def recall(self, query=""):
        if not self.data:
            return "I do not have any saved knowledge yet."
        q = query.lower().strip()
        if not q or q in ["all", "everything", "what do you remember"]:
            return "Saved knowledge:\n" + "\n".join([f"{k}: {v}" for k, v in sorted(self.data.items())])
        aliases = {"what is my browser": "browser", "my browser": "browser", "browser": "browser", "what ide do i use": "ide", "what is my ide": "ide", "my ide": "ide", "ide": "ide", "arduino com port": "arduino_com_port", "com port": "com_port"}
        key = aliases.get(q, self._simple_key(q))
        if key in self.data:
            return f"{key}: {self.data[key]}"
        matches = [f"{k}: {v}" for k, v in self.data.items() if q in k.lower() or q in str(v).lower()]
        return "\n".join(matches[:20]) if matches else f"I do not remember anything for: {query}"
