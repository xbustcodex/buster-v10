import sqlite3
from pathlib import Path
from datetime import datetime

class MemoryEngine:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, kind TEXT, value TEXT, created_at TEXT)")

    def add(self, kind: str, value: str):
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO memory(kind, value, created_at) VALUES (?, ?, ?)",
                       (kind, value, datetime.now().isoformat(timespec='seconds')))

    def recent(self, limit=10):
        with sqlite3.connect(self.db_path) as db:
            return db.execute("SELECT kind, value, created_at FROM memory ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def recent_clean(self, limit=8):
        return [f"{created_at[-8:]}  {kind}: {value[:80]}" for kind, value, created_at in self.recent(limit)]

    def search_text(self, query: str):
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("SELECT kind, value FROM memory WHERE value LIKE ? ORDER BY id DESC LIMIT 8",
                              (f"%{query}%",)).fetchall()
        if not rows:
            return "I found no matching memory."
        return "Memory results: " + " | ".join([f"{k}: {v}" for k, v in rows])
