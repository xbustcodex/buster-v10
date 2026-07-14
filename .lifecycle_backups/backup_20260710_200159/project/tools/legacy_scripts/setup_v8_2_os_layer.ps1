New-Item -ItemType Directory -Force "buster/os_layer" | Out-Null
New-Item -ItemType File -Force "buster/os_layer/__init__.py" | Out-Null

@'
from pathlib import Path
import os
import shutil
import subprocess

class FileSystemAccess:
    def __init__(self):
        self.home = Path.home()
        self.approved_roots = [
            self.home / "Desktop",
            self.home / "Documents",
            self.home / "Downloads",
            Path.cwd(),
        ]

    def roots(self):
        return [str(p) for p in self.approved_roots if p.exists()]

    def list_folder(self, folder):
        path = Path(folder).expanduser()
        if not path.exists():
            return f"Folder not found: {path}"

        lines = []
        for item in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))[:80]:
            kind = "DIR " if item.is_dir() else "FILE"
            lines.append(f"{kind}  {item.name}")

        return "\n".join(lines) if lines else "Folder is empty."

    def find_files(self, query, root=None, limit=80):
        q = query.lower()
        base = Path(root).expanduser() if root else Path.cwd()

        if not base.exists():
            return f"Search root not found: {base}"

        matches = []
        skip = {".git", ".venv", "venv", "build", "dist", "__pycache__"}

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

        os.startfile(str(path))
        return f"Opened: {path}"

    def disk_usage(self, path=None):
        base = Path(path).expanduser() if path else Path.cwd()
        usage = shutil.disk_usage(base)
        gb = 1024 ** 3
        return (
            f"Disk usage for {base}\n"
            f"Total: {usage.total / gb:.1f} GB\n"
            f"Used: {usage.used / gb:.1f} GB\n"
            f"Free: {usage.free / gb:.1f} GB"
        )
'@ | Set-Content "buster/os_layer/filesystem.py"

@'
import os
import subprocess

class WindowsSystemAccess:
    def env_summary(self):
        keys = ["USERNAME", "USERPROFILE", "COMPUTERNAME", "OS", "PROCESSOR_ARCHITECTURE"]
        return "\n".join(f"{k}: {os.environ.get(k, '')}" for k in keys)

    def where_python(self):
        try:
            result = subprocess.run(["where", "python"], capture_output=True, text=True, shell=True)
            return result.stdout.strip() or result.stderr.strip()
        except Exception as exc:
            return str(exc)

    def running_processes(self):
        try:
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                shell=True
            )
            return "\n".join(result.stdout.splitlines()[:40])
        except Exception as exc:
            return str(exc)
'@ | Set-Content "buster/os_layer/windows_system.py"

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
            return "Approved folders:\n" + "\n".join(self.fs.roots())

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
from buster.os_layer.os_layer import OSLayer

def test_os_layer_roots():
    os_layer = OSLayer()
    result = os_layer.handle("os roots")
    assert "Approved folders" in result

def test_os_layer_unknown():
    os_layer = OSLayer()
    assert os_layer.handle("unknown command") is None
'@ | Set-Content "tests/test_v8_2_os_layer.py"

@'
from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

if "from buster.os_layer.os_layer import OSLayer" not in text:
    text = text.replace(
        "from buster.version import VERSION\n",
        "from buster.version import VERSION\nfrom buster.os_layer.os_layer import OSLayer\n",
        1
    )

needle = "        cmd = text.strip().lower()\n"

insert = '''        os_reply = OSLayer().handle(text)
        if os_reply is not None:
            return os_reply

'''

if "os_reply = OSLayer().handle(text)" not in text:
    text = text.replace(needle, needle + insert, 1)

path.write_text(text, encoding="utf-8")
print("Buster OS Layer wired into BrainEngine.")
'@ | Set-Content "patch_v8_2_os_layer.py"

python patch_v8_2_os_layer.py

Write-Host "Buster OS Layer v8.2 foundation installed."