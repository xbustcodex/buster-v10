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
