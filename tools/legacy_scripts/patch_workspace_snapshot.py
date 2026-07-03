from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

if "WorkspaceSnapshot" not in text:

    text = text.replace(
        "from buster.os_layer.os_layer import OSLayer\n",
        "from buster.os_layer.os_layer import OSLayer\nfrom buster.workspace.runtime import WorkspaceSnapshot\n",
        1
    )

marker = "        os_reply = OSLayer().handle(text)\n"

insert = '''
        if cmd in [
            "workspace",
            "workspace snapshot",
            "workspace status"
        ]:
            return WorkspaceSnapshot().snapshot()

        if cmd=="git branch":
            return WorkspaceSnapshot().git_branch()

        if cmd=="git status":
            return WorkspaceSnapshot().git_status()

        if cmd=="python info":
            return WorkspaceSnapshot().python_info()

'''

if "workspace snapshot" not in text:
    text = text.replace(marker, insert + marker, 1)

path.write_text(text, encoding="utf-8")

print("Workspace Snapshot installed.")
