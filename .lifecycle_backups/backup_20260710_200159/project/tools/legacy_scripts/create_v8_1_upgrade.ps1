New-Item -ItemType Directory -Force assets, installer, ".github/workflows", "buster/updates", "buster/indexer" | Out-Null
New-Item -ItemType File -Force "buster/updates/__init__.py", "buster/indexer/__init__.py" | Out-Null

@'
import json
import urllib.request
from packaging import version

class UpdateChecker:
    def __init__(self, current_version, repo_url):
        self.current_version = current_version
        self.repo_url = repo_url.rstrip("/")

    def latest_release_api(self):
        return self.repo_url.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"

    def check(self):
        try:
            with urllib.request.urlopen(self.latest_release_api(), timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            latest = data.get("tag_name", "").lstrip("v")
            url = data.get("html_url", self.repo_url + "/releases")
            if latest and version.parse(latest) > version.parse(self.current_version):
                return True, latest, url
            return False, latest, url
        except Exception as exc:
            return False, None, str(exc)
'@ | Set-Content "buster/updates/updater.py"

@'
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Buster Settings")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("AI Provider"))
        self.provider = QComboBox()
        self.provider.addItems(["local", "ollama", "lmstudio", "openrouter"])
        layout.addWidget(self.provider)

        self.always_top = QCheckBox("Always on top")
        self.always_top.setChecked(getattr(settings, "always_on_top", False))
        layout.addWidget(self.always_top)

        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        layout.addWidget(save)
'@ | Set-Content "buster/ui/settings_dialog.py"

@'
import ast
from pathlib import Path

class ProjectIndexer:
    def __init__(self, root):
        self.root = Path(root)

    def scan(self):
        result = {"files": [], "classes": [], "functions": [], "imports": [], "todos": []}

        for path in self.root.rglob("*.py"):
            if any(skip in path.parts for skip in [".venv", "build", "dist", "__pycache__"]):
                continue

            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path.relative_to(self.root))
            result["files"].append(rel)

            for i, line in enumerate(text.splitlines(), 1):
                if "TODO" in line or "FIXME" in line:
                    result["todos"].append({"file": rel, "line": i, "text": line.strip()})

            try:
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        result["classes"].append({"name": node.name, "file": rel, "line": node.lineno})
                    elif isinstance(node, ast.FunctionDef):
                        result["functions"].append({"name": node.name, "file": rel, "line": node.lineno})
                    elif isinstance(node, ast.Import):
                        for n in node.names:
                            result["imports"].append({"name": n.name, "file": rel})
                    elif isinstance(node, ast.ImportFrom):
                        result["imports"].append({"name": node.module or "", "file": rel})
            except Exception:
                pass

        return result
'@ | Set-Content "buster/indexer/project_indexer.py"

@'
class ProjectQueryEngine:
    def __init__(self, index):
        self.index = index

    def ask(self, question):
        q = question.lower()

        if "todo" in q:
            return self.index.get("todos", [])

        if "vision" in q:
            return [x for x in self.index.get("files", []) if "vision" in x.lower()]

        if "planner" in q:
            return [x for x in self.index.get("files", []) if "planner" in x.lower()]

        if "function" in q:
            return self.index.get("functions", [])

        if "class" in q:
            return self.index.get("classes", [])

        return self.index
'@ | Set-Content "buster/indexer/query_engine.py"

@'
name: Build Windows EXE

on:
  push:
    tags:
      - "v*"

jobs:
  build:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build
        run: pyinstaller Buster.spec

      - name: Zip release
        run: Compress-Archive -Path dist\Buster\* -DestinationPath Buster-Windows.zip

      - name: Upload release
        uses: softprops/action-gh-release@v2
        with:
          files: Buster-Windows.zip
'@ | Set-Content ".github/workflows/windows-build.yml"

@'
[Setup]
AppName=Buster Companion
AppVersion=8.1.0
DefaultDirName={autopf}\Buster Companion
DefaultGroupName=Buster Companion
OutputDir=..\dist
OutputBaseFilename=BusterSetup-8.1.0
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\Buster\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Buster Companion"; Filename: "{app}\Buster.exe"
Name: "{commondesktop}\Buster Companion"; Filename: "{app}\Buster.exe"

[Run]
Filename: "{app}\Buster.exe"; Description: "Launch Buster"; Flags: nowait postinstall skipifsilent
'@ | Set-Content "installer/BusterSetup.iss"

Write-Host "Buster v8.1 upgrade files created."