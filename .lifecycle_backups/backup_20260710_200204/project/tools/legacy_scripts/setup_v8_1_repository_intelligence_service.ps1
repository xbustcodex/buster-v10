
New-Item -ItemType File -Force "buster/repository/__init__.py" | Out-Null

@'
from buster.intelligence.project_intelligence import ProjectIntelligence

class RepositoryIntelligenceService:
    def __init__(self, root="."):
        self.root = root
        self.project = ProjectIntelligence(root=root)

    def index(self):
        index = self.project.build_index()
        return (
            "Repository intelligence index rebuilt.\n"
            f"Files: {len(index['files'])}\n"
            f"Classes: {len(index['classes'])}\n"
            f"Functions: {len(index['functions'])}\n"
            f"Imports: {len(index['imports'])}\n"
            f"TODOs: {len(index['todos'])}"
        )

    def summary(self):
        return self.project.ask("project summary")

    def todos(self):
        return self.project.ask("show todos")

    def where_is(self, query):
        return self.project.find_references(query)

    def find_symbol(self, name):
        return self.project.find_symbol(name)

    def find_references(self, query):
        return self.project.find_references(query)

    def imports_of(self, package):
        return self.project.find_imports_of(package)

    def changed_since_index(self):
        return self.project.changed_since_index()
'@ | Set-Content "buster/repository/intelligence_service.py"

@'
from buster.repository.intelligence_service import RepositoryIntelligenceService

def test_repository_intelligence_service_summary():
    svc = RepositoryIntelligenceService(root=".")
    result = svc.summary()
    assert "Files:" in result

def test_repository_intelligence_service_index():
    svc = RepositoryIntelligenceService(root=".")
    result = svc.index()
    assert "Repository intelligence index rebuilt" in result
'@ | Set-Content "tests/test_v8_1_repository_intelligence_service.py"

@'
from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

if "from buster.repository.intelligence_service import RepositoryIntelligenceService" not in text:
    text = text.replace(
        "from buster.intelligence.project_intelligence import ProjectIntelligence\n",
        "from buster.intelligence.project_intelligence import ProjectIntelligence\nfrom buster.repository.intelligence_service import RepositoryIntelligenceService\n",
        1
    )

needle = "        cmd = text.strip().lower()\n"

commands = '''        repo_intel = RepositoryIntelligenceService(root=".")

        if cmd in ["index project", "reindex project", "index repository", "repo index"]:
            return repo_intel.index()

        if cmd in ["project summary", "project index", "codebase summary", "repository summary", "repo summary"]:
            return repo_intel.summary()

        if cmd in ["show todos", "show todo", "todos", "todo list"]:
            return repo_intel.todos()

        if cmd.startswith("find symbol "):
            return repo_intel.find_symbol(text[len("find symbol "):].strip())

        if cmd.startswith("find references "):
            return repo_intel.find_references(text[len("find references "):].strip())

        if cmd.startswith("imports of "):
            return repo_intel.imports_of(text[len("imports of "):].strip())

        if cmd.startswith("where is "):
            return repo_intel.where_is(text[len("where is "):].strip())

        if cmd in ["changed since index", "what changed since index"]:
            return repo_intel.changed_since_index()

'''

if "repo_intel = RepositoryIntelligenceService" not in text:
    text = text.replace(needle, needle + commands, 1)

path.write_text(text, encoding="utf-8")
print("BrainEngine wired to RepositoryIntelligenceService.")
'@ | Set-Content "patch_repository_intelligence_service.py"

python patch_repository_intelligence_service.py

Write-Host "Repository Intelligence Service installed."