New-Item -ItemType Directory -Force "buster/intelligence" | Out-Null
New-Item -ItemType File -Force "buster/intelligence/__init__.py" | Out-Null

@'
import ast
import json
from pathlib import Path
from datetime import datetime

SKIP_DIRS = {".venv", "build", "dist", "__pycache__", ".git", ".pytest_cache"}

class ProjectIntelligence:
    def __init__(self, root=".", output="data/project_index.json"):
        self.root = Path(root).resolve()
        self.output = Path(output)

    def should_skip(self, path: Path):
        return any(part in SKIP_DIRS for part in path.parts)

    def build_index(self):
        index = {
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "root": str(self.root),
            "files": [],
            "classes": [],
            "functions": [],
            "imports": [],
            "todos": [],
        }

        for path in self.root.rglob("*"):
            if self.should_skip(path) or not path.is_file():
                continue

            rel = str(path.relative_to(self.root))
            index["files"].append(rel)

            if path.suffix.lower() == ".py":
                self._scan_python(path, rel, index)
            else:
                self._scan_text(path, rel, index)

        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(index, indent=2), encoding="utf-8")
        return index

    def _scan_text(self, path, rel, index):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        for i, line in enumerate(text.splitlines(), 1):
            if "TODO" in line or "FIXME" in line:
                index["todos"].append({"file": rel, "line": i, "text": line.strip()})

    def _scan_python(self, path, rel, index):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        self._scan_text(path, rel, index)

        try:
            tree = ast.parse(text)
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                index["classes"].append({"name": node.name, "file": rel, "line": node.lineno})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                index["functions"].append({"name": node.name, "file": rel, "line": node.lineno})
            elif isinstance(node, ast.Import):
                for n in node.names:
                    index["imports"].append({"name": n.name, "file": rel, "line": node.lineno})
            elif isinstance(node, ast.ImportFrom):
                index["imports"].append({"name": node.module or "", "file": rel, "line": node.lineno})

    def load_index(self):
        if not self.output.exists():
            return self.build_index()
        return json.loads(self.output.read_text(encoding="utf-8"))

    def ask(self, question):
        q = question.lower()
        index = self.load_index()

        if "todo" in q:
            return self._format_items(index["todos"], "TODOs")

        if "vision" in q:
            files = [f for f in index["files"] if "vision" in f.lower()]
            return self._format_list(files, "Vision-related files")

        if "planner" in q:
            files = [f for f in index["files"] if "planner" in f.lower()]
            return self._format_list(files, "Planner-related files")

        if "class" in q:
            return self._format_items(index["classes"], "Classes")

        if "function" in q:
            return self._format_items(index["functions"], "Functions")

        if "import" in q:
            return self._format_items(index["imports"], "Imports")

        return (
            f"Project index:\n"
            f"Files: {len(index['files'])}\n"
            f"Classes: {len(index['classes'])}\n"
            f"Functions: {len(index['functions'])}\n"
            f"Imports: {len(index['imports'])}\n"
            f"TODOs: {len(index['todos'])}"
        )

    def _format_list(self, items, title):
        if not items:
            return f"{title}: none found."
        return title + ":\n" + "\n".join(f"- {x}" for x in items[:50])

    def _format_items(self, items, title):
        if not items:
            return f"{title}: none found."
        lines = []
        for item in items[:80]:
            name = item.get("name") or item.get("text", "")
            lines.append(f"- {name} — {item.get('file')}:{item.get('line')}")
        return title + ":\n" + "\n".join(lines)
'@ | Set-Content "buster/intelligence/project_intelligence.py"

@'
from buster.intelligence.project_intelligence import ProjectIntelligence

def test_project_intelligence_builds_index():
    pi = ProjectIntelligence(root=".", output="data/test_project_index.json")
    index = pi.build_index()
    assert "files" in index
    assert "classes" in index
    assert "functions" in index
    assert len(index["files"]) > 0

def test_project_intelligence_answers_summary():
    pi = ProjectIntelligence(root=".", output="data/test_project_index.json")
    answer = pi.ask("project summary")
    assert "Files:" in answer
'@ | Set-Content "tests/test_v8_1_project_intelligence.py"

Write-Host "Project Intelligence files created."