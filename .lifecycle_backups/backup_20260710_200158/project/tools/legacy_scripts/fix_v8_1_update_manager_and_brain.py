from pathlib import Path

ROOT = Path(".")
version_file = ROOT / "buster" / "version.py"
engine_file = ROOT / "buster" / "brain" / "engine.py"
patch_file = ROOT / "patch_update_manager.py"

# 1. Create central version file
version_file.write_text(
'''APP_NAME = "Buster Desktop Companion"
VERSION = "8.1.0"
BUILD = "2026.07.02"
''',
    encoding="utf-8",
)

# 2. Patch BrainEngine
text = engine_file.read_text(encoding="utf-8")

if "from buster.version import VERSION" not in text:
    text = text.replace(
        "from buster.updater.manager import UpdateManager\n",
        "from buster.updater.manager import UpdateManager\nfrom buster.version import VERSION\n",
    )

old_update_block = '''        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(
                current_version=getattr(self.services.get("settings"), "version", "8.1.0")
                if hasattr(self, "services") else "8.1.0"
            ).status_text()
'''

new_update_block = '''        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(current_version=VERSION).status_text()
'''

text = text.replace(old_update_block, new_update_block)

# 3. Remove old duplicate ProjectIntelligence block
start = text.find('''        
        if cmd.startswith("find symbol "):
            return ProjectIntelligence(root=".").find_symbol(text[len("find symbol "):].strip())
''')

end_marker = '''        if cmd in ["show imports", "list imports"]:
            return ProjectIntelligence(root=".").ask("show imports")

'''

if start != -1:
    end = text.find(end_marker, start)
    if end != -1:
        end += len(end_marker)
        text = text[:start] + "\n" + text[end:]

engine_file.write_text(text, encoding="utf-8")

# 4. Patch patch_update_manager.py so it does not re-add broken settings lookup
if patch_file.exists():
    ptext = patch_file.read_text(encoding="utf-8")

    if "from buster.version import VERSION" not in ptext:
        ptext = ptext.replace(
            "from buster.updater.manager import UpdateManager\\n",
            "from buster.updater.manager import UpdateManager\\nfrom buster.version import VERSION\\n",
        )

    old_patch_block = '''commands = \'''        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(
                current_version=getattr(self.services.get("settings"), "version", "8.1.0")
                if hasattr(self, "services") else "8.1.0"
            ).status_text()

\'''
'''

    new_patch_block = '''commands = \'''        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(current_version=VERSION).status_text()

\'''
'''

    ptext = ptext.replace(old_patch_block, new_patch_block)
    patch_file.write_text(ptext, encoding="utf-8")

print("Fixed v8.1 Update Manager + BrainEngine cleanup.")
print("Created buster/version.py")
print("Removed broken self.services.get('settings') lookup.")
print("Removed duplicate ProjectIntelligence handlers if found.")