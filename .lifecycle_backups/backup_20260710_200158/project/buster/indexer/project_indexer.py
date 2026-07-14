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
