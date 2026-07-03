from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

if "from buster.updater.manager import UpdateManager" not in text:
    text = text.replace(
        "from buster.repository.intelligence_service import RepositoryIntelligenceService\n",
        "from buster.repository.intelligence_service import RepositoryIntelligenceService\nfrom buster.updater.manager import UpdateManager\nfrom buster.version import VERSION\n",
        1
    )

needle = "        repo_intel = RepositoryIntelligenceService(root=\".\")\n"

commands = '''        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(current_version=VERSION).status_text()

'''

if "UpdateManager(" not in text:
    text = text.replace(needle, commands + needle, 1)

path.write_text(text, encoding="utf-8")
print("Update Manager command wired into BrainEngine.")
