@'
from pathlib import Path

target = Path("buster/brain/engine.py")
text = target.read_text(encoding="utf-8")

if "ProjectIntelligence" not in text:
    text = text.replace(
        "from buster.brain.planner.planner import AIPlanner\n",
        "from buster.brain.planner.planner import AIPlanner\nfrom buster.intelligence.project_intelligence import ProjectIntelligence\n",
        1
    )

marker = "    def process(self, text: str):\n"
insert = '''        cmd = text.strip().lower()

        if cmd in ["index project", "reindex project"]:
            pi = ProjectIntelligence(root=".")
            index = pi.build_index()
            return (
                "Project index rebuilt.\\n"
                f"Files: {len(index['files'])}\\n"
                f"Classes: {len(index['classes'])}\\n"
                f"Functions: {len(index['functions'])}\\n"
                f"Imports: {len(index['imports'])}\\n"
                f"TODOs: {len(index['todos'])}"
            )

        if cmd in ["project summary", "project index", "codebase summary"]:
            return ProjectIntelligence(root=".").ask("project summary")

        if cmd in ["show todos", "show todo", "todos", "todo list"]:
            return ProjectIntelligence(root=".").ask("show todos")

        if cmd in ["where is vision", "vision files", "find vision"]:
            return ProjectIntelligence(root=".").ask("where is vision")

        if cmd in ["which file defines the planner", "where is planner", "planner files", "find planner"]:
            return ProjectIntelligence(root=".").ask("which file defines the planner")

        if cmd in ["show classes", "list classes"]:
            return ProjectIntelligence(root=".").ask("show classes")

        if cmd in ["show functions", "list functions"]:
            return ProjectIntelligence(root=".").ask("show functions")

        if cmd in ["show imports", "list imports"]:
            return ProjectIntelligence(root=".").ask("show imports")

'''

if insert.strip() not in text:
    text = text.replace(marker, marker + insert, 1)

target.write_text(text, encoding="utf-8")
print("Wired Project Intelligence into buster/brain/engine.py")
'@ | Set-Content "wire_project_intelligence.py"

python wire_project_intelligence.py