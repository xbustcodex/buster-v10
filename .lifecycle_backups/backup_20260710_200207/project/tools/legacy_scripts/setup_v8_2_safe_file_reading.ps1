@'
from pathlib import Path
import os
import shutil
from buster.os_layer.approved_folders import ApprovedFolders

TEXT_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".bat", ".ps1", ".iss"
}

SKIP_PARTS = {
    ".git", ".venv", "venv", "build", "dist", "__pycache__",
    "backup's", "backups", ".old", ".bak"
}

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

    def should_skip(self, path):
        parts = {p.lower() for p in path.parts}
        name = path.name.lower()
        return bool(parts & SKIP_PARTS) or ".bak" in name

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
        seen = set()

        for base in bases:
            if not base.exists() or not self.is_approved(base):
                continue

            for path in base.rglob("*"):
                if self.should_skip(path):
                    continue

                if q in path.name.lower():
                    resolved = str(path.resolve())
                    key = resolved.lower()
                    if key not in seen:
                        seen.add(key)
                        matches.append(resolved)

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

    def read_file(self, target, max_chars=8000):
        path = Path(target).expanduser()

        if not path.exists():
            return f"File not found: {path}"

        if path.is_dir():
            return f"That is a folder, not a file: {path}"

        if not self.is_approved(path):
            return f"Access denied. Approve this folder first:\napprove folder {path.parent}"

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            return f"Unsupported file type for safe reading: {path.suffix}"

        text = path.read_text(encoding="utf-8", errors="ignore")

        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n--- truncated at {max_chars} characters ---"

        return text

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

        if low.startswith("read file "):
            return self.fs.read_file(cmd[len("read file "):].strip())

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

Write-Host "Safe file reading + cleaner search installed."