from pathlib import Path
import shutil
import re

ROOT = Path.cwd()
V9 = ROOT / "buster" / "ui" / "v9"
PANELS = V9 / "panels"

copies = {
    "runtime_dashboard.py": "runtime_overview_panel.py",
    "runtime_console.py": "runtime_console_panel.py",
    "mission_control.py": "mission_control_panel.py",
}

for src, dst in copies.items():
    s = PANELS / src
    d = PANELS / dst
    if s.exists():
        shutil.copy2(s, d)
        print(f"created/updated: {d}")

# make common UI files resizable
targets = [
    V9 / "main_window.py",
    V9 / "sidebar.py",
    V9 / "v9_shell.py",
    V9 / "chat_view.py",
]

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")
    backup = path.with_suffix(path.suffix + ".bak_resize")
    backup.write_text(text, encoding="utf-8")

    text = re.sub(r"\.setFixedSize\((.*?)\)", r".resize(\1)", text)
    text = re.sub(r"\.setFixedWidth\((.*?)\)", r".setMinimumWidth(\1)", text)
    text = re.sub(r"\.setFixedHeight\((.*?)\)", r".setMinimumHeight(\1)", text)

    path.write_text(text, encoding="utf-8")
    print(f"patched resize rules: {path}")

print("Done. Now run: python main.py")