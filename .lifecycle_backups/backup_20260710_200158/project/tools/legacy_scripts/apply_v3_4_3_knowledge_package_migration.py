from pathlib import Path
import shutil

ROOT = Path(__file__).parent
BUSTER = ROOT / "buster"
REPO = BUSTER / "repository"
KNOW = BUSTER / "knowledge"

KNOW.mkdir(parents=True, exist_ok=True)

def copy_module(name):
    src = REPO / name
    dst = KNOW / name
    if not src.exists():
        raise SystemExit(f"Missing source: {src}")
    shutil.copy2(src, dst)
    print("copied:", src, "->", dst)

copy_module("intelligence.py")
copy_module("semantic_graph.py")
copy_module("knowledge_engine.py")

# Fix imports inside the new knowledge package
for file in [
    KNOW / "knowledge_engine.py",
]:
    text = file.read_text(encoding="utf-8")
    text = text.replace(
        "from buster.knowledge.intelligence import RepositoryIntelligenceBuilder",
        "from buster.knowledge.intelligence import RepositoryIntelligenceBuilder",
    )
    text = text.replace(
        "from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder",
        "from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder",
    )
    file.write_text(text, encoding="utf-8")
    print("patched imports:", file)

# New package init
(KNOW / "__init__.py").write_text(r'''
from .intelligence import RepositoryIntelligenceBuilder, RepositoryIntelligence
from .semantic_graph import SemanticRepositoryGraphBuilder, SemanticRepositoryGraph
from .knowledge_engine import RepositoryKnowledgeEngine, RepositoryKnowledge, FileKnowledge

__all__ = [
    "RepositoryIntelligenceBuilder",
    "RepositoryIntelligence",
    "SemanticRepositoryGraphBuilder",
    "SemanticRepositoryGraph",
    "RepositoryKnowledgeEngine",
    "RepositoryKnowledge",
    "FileKnowledge",
]
'''.strip() + "\n", encoding="utf-8")

print("wrote:", KNOW / "__init__.py")

# Leave compatibility wrappers in old repository paths
(REPO / "intelligence.py").write_text(r'''
from buster.knowledge.intelligence import *
'''.strip() + "\n", encoding="utf-8")

(REPO / "semantic_graph.py").write_text(r'''
from buster.knowledge.semantic_graph import *
'''.strip() + "\n", encoding="utf-8")

(REPO / "knowledge_engine.py").write_text(r'''
from buster.knowledge.knowledge_engine import *
'''.strip() + "\n", encoding="utf-8")

print("wrote compatibility wrappers in buster/repository")

# Update known direct imports in project files
for path in ROOT.rglob("*.py"):
    if "__pycache__" in path.parts:
        continue
    if ".git" in path.parts:
        continue
    if path.parts and "buster_desktop_companion_v3_0_developer_edition" in path.parts[len(ROOT.parts):len(ROOT.parts)+1]:
        continue

    text = path.read_text(encoding="utf-8", errors="ignore")
    old = text

    text = text.replace(
        "from buster.knowledge.intelligence import",
        "from buster.knowledge.intelligence import",
    )
    text = text.replace(
        "from buster.knowledge.semantic_graph import",
        "from buster.knowledge.semantic_graph import",
    )
    text = text.replace(
        "from buster.knowledge.knowledge_engine import",
        "from buster.knowledge.knowledge_engine import",
    )

    if text != old:
        path.write_text(text, encoding="utf-8")
        print("updated imports:", path)

test = ROOT / "test_v3_4_3_knowledge_package_migration.py"
test.write_text(r'''
from pathlib import Path

from buster.knowledge import RepositoryKnowledgeEngine
from buster.knowledge.intelligence import RepositoryIntelligenceBuilder
from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder

# compatibility imports should also still work
from buster.knowledge.knowledge_engine import RepositoryKnowledgeEngine as CompatKnowledgeEngine


def main():
    root = Path(__file__).parent

    intel = RepositoryIntelligenceBuilder(root).build()
    graph = SemanticRepositoryGraphBuilder(root).build()
    engine = RepositoryKnowledgeEngine(root)
    engine.build()

    compat = CompatKnowledgeEngine(root)
    compat.build()

    print("=== Buster v3.4.3 Knowledge Package Migration Test ===")
    print("Knowledge package OK")
    print("Symbols:", len(intel.symbols))
    print("Calls:", len(graph.calls))
    print("Files:", engine.stats()["files"])
    print("Compat files:", compat.stats()["files"])

    print()
    print(engine.ask("Which classes inherit Agent?"))

    print()
    print("SUCCESS: v3.4.3 Knowledge Package Migration installed.")


if __name__ == "__main__":
    main()
'''.strip() + "\n", encoding="utf-8")

print("wrote:", test)

print()
print("Buster v3.4.3 Knowledge Package Migration patch complete.")
print("Run:")
print("python test_v3_4_3_knowledge_package_migration.py")