from pathlib import Path
import subprocess
import sys

class V9LiveServices:
    def __init__(self, services=None, settings=None):
        self.services = services
        self.settings = settings

    def safe(self, fn, fallback="unknown"):
        try:
            return fn()
        except Exception:
            return fallback

    def brain(self, text):
        if not self.services:
            return "No brain service connected."
        return self.services.get("brain").process(text)

    def git_branch(self):
        r = subprocess.run("git branch --show-current", capture_output=True, text=True, shell=True)
        return r.stdout.strip() or "unknown"

    def python_version(self):
        return sys.version.split()[0]

    def quick_info(self):
        ai = self.safe(lambda: self.services.get("ai").quick_status(), "unknown")
        return (
            "QUICK INFO\n\n"
            f"AI Provider      {ai}\n"
            f"Workspace        {Path.cwd().name}\n"
            f"Git Branch       {self.git_branch()}\n"
            f"Python           {self.python_version()}\n"
            "Internet         Connected\n\n"
            "● Buster v9.0.0"
        )
