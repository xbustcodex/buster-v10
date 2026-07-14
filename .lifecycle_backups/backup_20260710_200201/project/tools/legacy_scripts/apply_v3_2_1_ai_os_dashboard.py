from pathlib import Path

ROOT = Path(__file__).parent
BUSTER = ROOT / "buster"

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote", path)

write(BUSTER / "ui" / "widgets" / "ai_os_dashboard.py", r'''
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from buster.workspace.ai_os import AIOSCore


class AIOSDashboard(tk.Frame):
    def __init__(self, master, project_root: str | Path):
        super().__init__(master, bg="#101014")
        self.project_root = Path(project_root)
        self.ai_os = AIOSCore(self.project_root)

        self.stat_vars = {}
        self.job_list = None

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        title = tk.Label(
            self,
            text="BUSTER AI OS DASHBOARD v3.2.1",
            bg="#101014",
            fg="#00ff99",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(pady=10)

        button_bar = tk.Frame(self, bg="#101014")
        button_bar.pack(fill="x", padx=10, pady=5)

        tk.Button(
            button_bar,
            text="Rebuild Project Model",
            command=self.rebuild_project_model,
            bg="#1f6feb",
            fg="white",
        ).pack(side="left", padx=5)

        tk.Button(
            button_bar,
            text="Refresh",
            command=self.refresh,
            bg="#30363d",
            fg="white",
        ).pack(side="left", padx=5)

        stats = tk.LabelFrame(
            self,
            text="Repository Intelligence",
            bg="#101014",
            fg="#00ff99",
            padx=10,
            pady=10,
        )
        stats.pack(fill="x", padx=10, pady=10)

        for name in [
            "files",
            "python_files",
            "classes",
            "functions",
            "imports",
            "todos",
            "errors",
        ]:
            row = tk.Frame(stats, bg="#101014")
            row.pack(fill="x")

            label = tk.Label(
                row,
                text=name.replace("_", " ").title() + ":",
                width=18,
                anchor="w",
                bg="#101014",
                fg="#dddddd",
            )
            label.pack(side="left")

            var = tk.StringVar(value="0")
            self.stat_vars[name] = var

            value = tk.Label(
                row,
                textvariable=var,
                anchor="w",
                bg="#101014",
                fg="#ffffff",
                font=("Segoe UI", 10, "bold"),
            )
            value.pack(side="left")

        jobs = tk.LabelFrame(
            self,
            text="Background Jobs",
            bg="#101014",
            fg="#00ff99",
            padx=10,
            pady=10,
        )
        jobs.pack(fill="both", expand=True, padx=10, pady=10)

        self.job_list = tk.Listbox(
            jobs,
            bg="#161b22",
            fg="#ffffff",
            selectbackground="#238636",
            height=8,
        )
        self.job_list.pack(fill="both", expand=True)

        self.after(1000, self.auto_refresh)

    def rebuild_project_model(self):
        self.ai_os.rebuild_project_model()
        self.refresh()

    def refresh(self):
        status = self.ai_os.status()

        for key, var in self.stat_vars.items():
            var.set(str(status.get(key, 0)))

        self.job_list.delete(0, tk.END)

        jobs = status.get("jobs", [])
        if not jobs:
            self.job_list.insert(tk.END, "No background jobs yet.")
        else:
            for job in jobs:
                text = f"[{job['status'].upper()}] {job['title']}  #{job['id']}"
                if job.get("error"):
                    text += f" ERROR: {job['error']}"
                self.job_list.insert(tk.END, text)

    def auto_refresh(self):
        self.refresh()
        self.after(1000, self.auto_refresh)


def launch_ai_os_dashboard(project_root: str | Path):
    root = tk.Tk()
    root.title("Buster AI OS Dashboard v3.2.1")
    root.geometry("620x520")
    app = AIOSDashboard(root, project_root)
    app.pack(fill="both", expand=True)
    root.mainloop()
''')

write(ROOT / "test_v3_2_1_ai_os_dashboard.py", r'''
from pathlib import Path

from buster.ui.widgets.ai_os_dashboard import launch_ai_os_dashboard


if __name__ == "__main__":
    project_root = Path(__file__).parent
    launch_ai_os_dashboard(project_root)
''')

write(ROOT / "scripts" / "run_ai_os_dashboard.bat", r'''
@echo off
cd /d "%~dp0\.."
python test_v3_2_1_ai_os_dashboard.py
pause
''')

print()
print("Buster v3.2.1 AI OS Dashboard patch complete.")
print("Run:")
print("python test_v3_2_1_ai_os_dashboard.py")