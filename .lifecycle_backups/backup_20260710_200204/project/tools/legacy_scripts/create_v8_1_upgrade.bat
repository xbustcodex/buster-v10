@echo off
setlocal

echo Creating Buster v8.1 upgrade files...

mkdir assets 2>nul
mkdir installer 2>nul
mkdir .github\workflows 2>nul
mkdir buster\updates 2>nul
mkdir buster\indexer 2>nul

type nul > buster\updates\__init__.py
type nul > buster\indexer\__init__.py

echo Done folders.

echo Creating updater...
(
echo import json
echo import urllib.request
echo from packaging import version
echo.
echo class UpdateChecker:
echo     def __init__(self, current_version, repo_url):
echo         self.current_version = current_version
echo         self.repo_url = repo_url.rstrip("/")
echo.
echo     def latest_release_api(self):
echo         return self.repo_url.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
echo.
echo     def check(self):
echo         try:
echo             with urllib.request.urlopen(self.latest_release_api(), timeout=8) as r:
echo                 data = json.loads(r.read().decode("utf-8"))
echo             latest = data.get("tag_name", "").lstrip("v")
echo             url = data.get("html_url", self.repo_url + "/releases")
echo             if latest and version.parse(latest) ^> version.parse(self.current_version):
echo                 return True, latest, url
echo             return False, latest, url
echo         except Exception as exc:
echo             return False, None, str(exc)
) > buster\updates\updater.py

echo Creating settings dialog...
(
echo from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton
echo.
echo class SettingsDialog(QDialog):
echo     def __init__(self, settings, parent=None):
echo         super().__init__(parent)
echo         self.settings = settings
echo         self.setWindowTitle("Buster Settings")
echo         layout = QVBoxLayout(self)
echo.
echo         layout.addWidget(QLabel("AI Provider"))
echo         self.provider = QComboBox()
echo         self.provider.addItems(["local", "ollama", "lmstudio", "openrouter"])
echo         layout.addWidget(self.provider)
echo.
echo         self.always_top = QCheckBox("Always on top")
echo         self.always_top.setChecked(getattr(settings, "always_on_top", False))
echo         layout.addWidget(self.always_top)
echo.
echo         save = QPushButton("Save")
echo         save.clicked.connect(self.accept)
echo         layout.addWidget(save)
) > buster\ui\settings_dialog.py

echo Creating project indexer...
(
echo import ast
echo from pathlib import Path
echo.
echo class ProjectIndexer:
echo     def __init__(self, root):
echo         self.root = Path(root)
echo.
echo     def scan(self):
echo         result = {"files": [], "classes": [], "functions": [], "imports": [], "todos": []}
echo         for path in self.root.rglob("*.py"):
echo             if any(skip in path.parts for skip in [".venv", "build", "dist", "__pycache__"]):
echo                 continue
echo             text = path.read_text(encoding="utf-8", errors="ignore")
echo             rel = str(path.relative_to(self.root))
echo             result["files"].append(rel)
echo             for i, line in enumerate(text.splitlines(), 1):
echo                 if "TODO" in line or "FIXME" in line:
echo                     result["todos"].append({"file": rel, "line": i, "text": line.strip()})
echo             try:
echo                 tree = ast.parse(text)
echo                 for node in ast.walk(tree):
echo                     if isinstance(node, ast.ClassDef):
echo                         result["classes"].append({"name": node.name, "file": rel, "line": node.lineno})
echo                     elif isinstance(node, ast.FunctionDef):
echo                         result["functions"].append({"name": node.name, "file": rel, "line": node.lineno})
echo                     elif isinstance(node, ast.Import):
echo                         for n in node.names:
echo                             result["imports"].append({"name": n.name, "file": rel})
echo                     elif isinstance(node, ast.ImportFrom):
echo                         result["imports"].append({"name": node.module or "", "file": rel})
echo             except Exception:
echo                 pass
echo         return result
) > buster\indexer\project_indexer.py

echo Creating query engine...
(
echo class ProjectQueryEngine:
echo     def __init__(self, index):
echo         self.index = index
echo.
echo     def ask(self, question):
echo         q = question.lower()
echo         if "todo" in q:
echo             return self.index.get("todos", [])
echo         if "vision" in q:
echo             return [x for x in self.index.get("files", []) if "vision" in x.lower()]
echo         if "planner" in q:
echo             return [x for x in self.index.get("files", []) if "planner" in x.lower()]
echo         if "function" in q:
echo             return self.index.get("functions", [])
echo         if "class" in q:
echo             return self.index.get("classes", [])
echo         return self.index
) > buster\indexer\query_engine.py

echo Creating GitHub Actions workflow...
(
echo name: Build Windows EXE
echo.
echo on:
echo   push:
echo     tags:
echo       - "v*"
echo.
echo jobs:
echo   build:
echo     runs-on: windows-latest
echo.
echo     steps:
echo       - uses: actions/checkout@v4
echo.
echo       - uses: actions/setup-python@v5
echo         with:
echo           python-version: "3.12"
echo.
echo       - name: Install dependencies
echo         run: ^
echo           python -m pip install --upgrade pip ^
echo           pip install -r requirements.txt ^
echo           pip install pyinstaller
echo.
echo       - name: Build
echo         run: pyinstaller Buster.spec
echo.
echo       - name: Zip release
echo         run: Compress-Archive -Path dist\Buster\* -DestinationPath Buster-Windows.zip
echo.
echo       - name: Upload release
echo         uses: softprops/action-gh-release@v2
echo         with:
echo           files: Buster-Windows.zip
) > .github\workflows\windows-build.yml

echo Creating Inno Setup installer script...
(
echo [Setup]
echo AppName=Buster Companion
echo AppVersion=8.1.0
echo DefaultDirName={autopf}\Buster Companion
echo DefaultGroupName=Buster Companion
echo OutputDir=dist
echo OutputBaseFilename=BusterSetup-8.1.0
echo Compression=lzma
echo SolidCompression=yes
echo.
echo [Files]
echo Source: "..\dist\Buster\*"; DestDir: "{app}"; Flags: recursesubdirs
echo.
echo [Icons]
echo Name: "{group}\Buster Companion"; Filename: "{app}\Buster.exe"
echo Name: "{commondesktop}\Buster Companion"; Filename: "{app}\Buster.exe"
echo.
echo [Run]
echo Filename: "{app}\Buster.exe"; Description: "Launch Buster"; Flags: nowait postinstall skipifsilent
) > installer\BusterSetup.iss

echo.
echo Buster v8.1 files created.
echo Next:
echo 1. Add icon: assets\buster.ico
echo 2. Update Buster.spec icon="assets/buster.ico"
echo 3. Run scripts\build_exe.bat
echo 4. Build installer with Inno Setup
pause