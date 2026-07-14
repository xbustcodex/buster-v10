@'
from pathlib import Path

path = Path("buster/intelligence/project_intelligence.py")
text = path.read_text(encoding="utf-8")

if "def find_symbol" not in text:
    insert = '''
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

'''
    text = text.replace("    def _format_list(self, items, title):", insert + "\n    def _format_list(self, items, title):")

path.write_text(text, encoding="utf-8")
print("Project Intelligence v2 methods added.")
'@ | Set-Content "patch_project_intelligence_v2.py"

python patch_project_intelligence_v2.py

@'
from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

marker = '        if cmd in ["show imports", "list imports"]:\n            return ProjectIntelligence(root=".").ask("show imports")\n'

add = '''
        if cmd.startswith("find symbol "):
            return ProjectIntelligence(root=".").find_symbol(text[len("find symbol "):].strip())

        if cmd.startswith("find references "):
            return ProjectIntelligence(root=".").find_references(text[len("find references "):].strip())

        if cmd.startswith("where is "):
            query = text[len("where is "):].strip()
            return ProjectIntelligence(root=".").find_references(query)

        if cmd.startswith("imports of "):
            return ProjectIntelligence(root=".").find_imports_of(text[len("imports of "):].strip())

        if cmd in ["changed since index", "what changed since index"]:
            return ProjectIntelligence(root=".").changed_since_index()

'''

if "find_symbol(" not in text:
    text = text.replace(marker, marker + add)

path.write_text(text, encoding="utf-8")
print("Project Intelligence v2 commands wired.")
'@ | Set-Content "patch_brain_project_intelligence_v2.py"

python patch_brain_project_intelligence_v2.py

Write-Host "Project Intelligence v2 installed."