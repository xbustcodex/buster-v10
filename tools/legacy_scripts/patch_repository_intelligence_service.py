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
