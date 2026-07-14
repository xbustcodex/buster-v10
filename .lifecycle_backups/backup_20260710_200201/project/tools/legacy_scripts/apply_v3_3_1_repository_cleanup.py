from pathlib import Path
import shutil

ROOT = Path(__file__).parent
TARGET = ROOT / "buster" / "repository" / "intelligence.py"
BACKUP = TARGET.with_suffix(".py.bak_v331")

shutil.copy2(TARGET, BACKUP)
print("backup:", BACKUP)

text = TARGET.read_text(encoding="utf-8")

text = text.replace(
'''class RepositoryIntelligenceBuilder:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def build(self) -> RepositoryIntelligence:
        intel = RepositoryIntelligence(root=str(self.root))
        file_infos = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if "__pycache__" in path.parts:
                continue

            if ".git" in path.parts:
                continue

            rel = str(path.relative_to(self.root))
''',
'''class RepositoryIntelligenceBuilder:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.ignore_dirs = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            "models",
        }
        self.ignore_suffixes = {
            ".pyc",
            ".pyo",
            ".pt",
            ".onnx",
            ".db",
            ".sqlite",
            ".sqlite3",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".mp4",
            ".avi",
            ".zip",
        }

    def _should_ignore(self, path: Path) -> bool:
        rel_parts = path.relative_to(self.root).parts

        if any(part in self.ignore_dirs for part in rel_parts):
            return True

        if path.suffix.lower() in self.ignore_suffixes:
            return True

        # Ignore old nested duplicate copy of the project.
        if rel_parts and rel_parts[0] == self.root.name:
            return True

        # Patch scripts are useful, but should not pollute repository intelligence.
        if path.name.startswith("apply_v") and path.suffix == ".py":
            return True

        return False

    def build(self) -> RepositoryIntelligence:
        intel = RepositoryIntelligence(root=str(self.root))
        file_infos = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if self._should_ignore(path):
                continue

            rel = str(path.relative_to(self.root))
'''
)

text = text.replace(
'''        intel.largest_files = sorted(file_infos, key=lambda x: x.size, reverse=True)[:30]
        return intel
''',
'''        intel.symbols = self._dedupe(intel.symbols)
        intel.imports = self._dedupe(intel.imports)
        intel.todos = self._dedupe(intel.todos)
        intel.test_files = sorted(set(intel.test_files))
        intel.largest_files = sorted(file_infos, key=lambda x: x.size, reverse=True)[:30]
        return intel

    def _dedupe(self, items):
        seen = set()
        clean = []

        for item in items:
            key = tuple(sorted(item.__dict__.items()))
            if key in seen:
                continue
            seen.add(key)
            clean.append(item)

        return clean
'''
)

text = text.replace(
'''        if "vision engine" in q:
            return self._where_file_or_symbol("vision", "engine")
''',
'''        if "vision engine" in q:
            matches = [
                s for s in self.symbols
                if "buster\\\\vision\\\\engine.py" in s.file.replace("/", "\\\\").lower()
                and ("VisionEngine" in s.name or s.kind in ("class", "method"))
            ]
            return self._format_matches(matches[:20], "Vision engine")
'''
)

TARGET.write_text(text, encoding="utf-8")
print("patched:", TARGET)

test = ROOT / "test_v3_3_1_repository_cleanup.py"
test.write_text(r'''
from pathlib import Path

from buster.knowledge.intelligence import RepositoryIntelligenceBuilder


def main():
    root = Path(__file__).parent
    intel = RepositoryIntelligenceBuilder(root).build()

    print("=== Buster v3.3.1 Repository Cleanup Test ===")
    print("Symbols:", len(intel.symbols))
    print("Imports:", len(intel.imports))
    print("TODOs:", len(intel.todos))
    print("Largest files:", len(intel.largest_files))
    print("Test files:", len(intel.test_files))
    print("Errors:", len(intel.errors))

    print()
    print("Largest files:")
    for f in intel.largest_files[:10]:
        print(f"- {f.file} | {f.lines} lines | {f.size} bytes")

    print()
    print('Ask: "Where is vision engine?"')
    print(intel.ask("Where is vision engine?"))

    bad = [
        f.file for f in intel.largest_files
        if f.file.endswith(".pt")
        or f.file.endswith(".db")
        or f.file.startswith("apply_v")
        or f.file.startswith(root.name)
    ]

    if bad:
        print()
        print("Cleanup failed. Bad files still indexed:")
        for item in bad:
            print("-", item)
        raise SystemExit(1)

    print()
    print("SUCCESS: v3.3.1 Repository Cleanup installed.")


if __name__ == "__main__":
    main()
'''.strip() + "\n", encoding="utf-8")

print("wrote:", test)
print()
print("Run:")
print("python test_v3_3_1_repository_cleanup.py")