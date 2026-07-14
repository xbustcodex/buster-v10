import ast
import json
from pathlib import Path
from datetime import datetime

TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".bat", ".ps1"
}


SKIP_DIRS = {
    ".venv", "build", "dist", "__pycache__", ".git", ".pytest_cache",
    ".mypy_cache", ".ruff_cache"
}

SKIP_FILES_PREFIX = (
    "apply_",
    "patch_",
    "test_",
    "wire_",
    "setup_",
    "create_",
)

SKIP_FILES_SUFFIX = (
    ".bak",
    ".bak_vision_thread_fix",
)

class ProjectIntelligence:
    def __init__(self, root=".", output="data/project_index.json"):
        self.root = Path(root).resolve()
        self.output = Path(output)

    def should_skip(self, path: Path):
        path_str = str(path).replace("\\", "/").lower()
        name = path.name.lower()
        parts = {p.lower() for p in path.parts}

        if path_str.endswith("data/project_index.json"):
            return True

        if name.startswith(SKIP_FILES_PREFIX):
            return True

        if name.endswith(SKIP_FILES_SUFFIX):
            return True

        if ".bak_" in name:
            return True

        if name.endswith(".pyc"):
            return True

        if "__pycache__" in parts:
            return True

        if ".venv" in parts or "venv" in parts:
            return True

        if "dist" in parts or "build" in parts:
            return True

        if ".git" in parts:
            return True

        if any(part in SKIP_DIRS for part in path.parts):
            return True

        return False

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

            suffix = path.suffix.lower()

            if suffix == ".py":
                self._scan_python(path, rel, index)
            elif suffix in TEXT_EXTENSIONS:
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
            clean = line.strip().upper()
            if clean.startswith(("TODO:", "# TODO", "// TODO", "FIXME:", "# FIXME", "// FIXME")):
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


    def find_symbol(self, name):
        q = name.lower()
        index = self.load_index()

        matches = []
        for item in index.get("classes", []) + index.get("functions", []):
            if q in item.get("name", "").lower():
                matches.append(item)

        return self._format_items(matches, f"Symbol search: {name}")

    def find_references(self, query):
        q = query.lower()
        index = self.load_index()
        matches = []

        for file in index.get("files", []):
            path = self.root / file
            if not path.exists() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            try:
                for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if q in line.lower():
                        matches.append({"name": line.strip()[:120], "file": file, "line": i})
            except Exception:
                pass

        return self._format_items(matches, f"References: {query}")

    def find_imports_of(self, package):
        q = package.lower()
        index = self.load_index()

        matches = [
            item for item in index.get("imports", [])
            if q in item.get("name", "").lower()
        ]

        return self._format_items(matches, f"Imports matching: {package}")

    def changed_since_index(self):
        index = self.load_index()
        changed = []

        for file in index.get("files", []):
            path = self.root / file
            if not path.exists():
                changed.append(f"Deleted: {file}")
                continue

            try:
                mtime = path.stat().st_mtime
                # simple check: compare to index file timestamp
                if mtime > self.output.stat().st_mtime:
                    changed.append(f"Modified: {file}")
            except Exception:
                pass

        return self._format_list(changed, "Changed since last index")


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
