@'
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
'@ | Set-Content "buster/os_layer/approved_folders.py"

@'
from pathlib import Path
import os
import shutil
from buster.os_layer.approved_folders import ApprovedFolders

class FileSystemAccess:
    def __init__(self):
        self.approved = ApprovedFolders()

    def roots(self):
        return self.approved.load()

    def is_approved(self, path):
        p = Path(path).expanduser().resolve()
        for root in self.roots():
            try:
                p.relative_to(Path(root).resolve())
                return True
            except Exception:
                pass
        return False

    def list_folder(self, folder):
        path = Path(folder).expanduser()

        if not path.exists():
            return f"Folder not found: {path}"

        if not self.is_approved(path):
            return f"Access denied. Approve this folder first:\napprove folder {path}"

        lines = []
        for item in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))[:100]:
            kind = "DIR " if item.is_dir() else "FILE"
            lines.append(f"{kind}  {item.name}")

        return "\n".join(lines) if lines else "Folder is empty."

    def find_files(self, query, root=None, limit=100):
        q = query.lower()

        if root:
            bases = [Path(root).expanduser()]
        else:
            bases = [Path(r) for r in self.roots()]

        matches = []
        skip = {".git", ".venv", "venv", "build", "dist", "__pycache__"}

        for base in bases:
            if not base.exists():
                continue

            if not self.is_approved(base):
                continue

            for path in base.rglob("*"):
                if any(part in skip for part in path.parts):
                    continue
                if q in path.name.lower():
                    matches.append(str(path))
                if len(matches) >= limit:
                    break

        return "\n".join(matches) if matches else f"No files found matching: {query}"

    def open_path(self, target):
        path = Path(target).expanduser()

        if not path.exists():
            return f"Path not found: {path}"

        if not self.is_approved(path):
            return f"Access denied. Approve this path first:\napprove folder {path.parent}"

        os.startfile(str(path))
        return f"Opened: {path}"

    def disk_usage(self, path=None):
        base = Path(path).expanduser() if path else Path.cwd()

        if not self.is_approved(base):
            return f"Access denied. Approve this folder first:\napprove folder {base}"

        usage = shutil.disk_usage(base)
        gb = 1024 ** 3
        return (
            f"Disk usage for {base}\n"
            f"Total: {usage.total / gb:.1f} GB\n"
            f"Used: {usage.used / gb:.1f} GB\n"
            f"Free: {usage.free / gb:.1f} GB"
        )

    def approve_folder(self, folder):
        return self.approved.add(folder)[1]

    def remove_folder(self, folder):
        return self.approved.remove(folder)[1]

    def approved_folders(self):
        return self.approved.list_text()
'@ | Set-Content "buster/os_layer/filesystem.py"

@'
from buster.os_layer.filesystem import FileSystemAccess
from buster.os_layer.windows_system import WindowsSystemAccess

class OSLayer:
    def __init__(self):
        self.fs = FileSystemAccess()
        self.windows = WindowsSystemAccess()

    def handle(self, text):
        cmd = text.strip()
        low = cmd.lower()

        if low in ["os roots", "approved folders"]:
            return self.fs.approved_folders()

        if low.startswith("approve folder "):
            return self.fs.approve_folder(cmd[len("approve folder "):].strip())

        if low.startswith("remove approved folder "):
            return self.fs.remove_folder(cmd[len("remove approved folder "):].strip())

        if low in ["list downloads", "show downloads"]:
            return self.fs.list_folder("~/Downloads")

        if low in ["list desktop", "show desktop"]:
            return self.fs.list_folder("~/Desktop")

        if low in ["list documents", "show documents"]:
            return self.fs.list_folder("~/Documents")

        if low.startswith("list folder "):
            return self.fs.list_folder(cmd[len("list folder "):].strip())

        if low.startswith("open file "):
            return self.fs.open_path(cmd[len("open file "):].strip())

        if low.startswith("open folder "):
            return self.fs.open_path(cmd[len("open folder "):].strip())

        if low.startswith("find file "):
            return self.fs.find_files(cmd[len("find file "):].strip())

        if low.startswith("search files "):
            return self.fs.find_files(cmd[len("search files "):].strip())

        if low in ["disk usage", "disk space"]:
            return self.fs.disk_usage()

        if low in ["env", "environment"]:
            return self.windows.env_summary()

        if low in ["where python", "python path"]:
            return self.windows.where_python()

        if low in ["processes", "running processes"]:
            return self.windows.running_processes()

        return None
'@ | Set-Content "buster/os_layer/os_layer.py"

@'
from buster.os_layer.approved_folders import ApprovedFolders
from buster.os_layer.os_layer import OSLayer

def test_approved_folders_loads():
    folders = ApprovedFolders(path="data/test_approved_folders.json")
    assert isinstance(folders.load(), list)

def test_os_layer_roots():
    result = OSLayer().handle("approved folders")
    assert "Approved folders" in result
'@ | Set-Content "tests/test_v8_2_approved_folders.py"

Write-Host "Approved folder management installed."