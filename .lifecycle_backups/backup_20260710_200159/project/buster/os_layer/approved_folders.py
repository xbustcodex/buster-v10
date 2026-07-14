import json
from pathlib import Path

class ApprovedFolders:
    def __init__(self, path="data/approved_folders.json"):
        self.path = Path(path)

    def defaults(self):
        home = Path.home()
        roots = [
            home / "Documents",
            home / "Downloads",
            Path.cwd(),
        ]
        desktop = home / "Desktop"
        if desktop.exists():
            roots.insert(0, desktop)
        return [str(p) for p in roots if p.exists()]

    def load(self):
        if not self.path.exists():
            self.save(self.defaults())
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("folders", self.defaults())
        except Exception:
            return self.defaults()

    def save(self, folders):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        clean = []
        for folder in folders:
            p = Path(folder).expanduser()
            if p.exists():
                value = str(p.resolve())
                if value not in clean:
                    clean.append(value)
        self.path.write_text(json.dumps({"folders": clean}, indent=2), encoding="utf-8")

    def add(self, folder):
        p = Path(folder).expanduser()
        if not p.exists():
            return False, f"Folder not found: {p}"

        folders = self.load()
        value = str(p.resolve())
        if value not in folders:
            folders.append(value)
            self.save(folders)

        return True, f"Approved folder added:\n{value}"

    def remove(self, folder):
        target = str(Path(folder).expanduser().resolve())
        folders = self.load()
        new_folders = [f for f in folders if str(Path(f).resolve()).lower() != target.lower()]
        self.save(new_folders)
        return True, f"Approved folder removed:\n{target}"

    def list_text(self):
        return "Approved folders:\n" + "\n".join(self.load())
