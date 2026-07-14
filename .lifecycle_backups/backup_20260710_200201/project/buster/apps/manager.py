import json
import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

class ApplicationManager:
    def __init__(self, cache_file):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.apps = {}
        self.refresh()

    def refresh(self):
        self.apps = self.detect_known_apps()
        self.cache_file.write_text(json.dumps(self.apps, indent=2), encoding="utf-8")
        return f"Found {len(self.apps)} applications."

    def detect_known_apps(self):
        user = Path.home()
        known = {
            "Microsoft Edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "msedge"],
            "Mozilla Firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe", r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe", "firefox"],
            "Google Chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", str(user / r"AppData\Local\Google\Chrome\Application\chrome.exe"), "chrome"],
            "Visual Studio Code": [str(user / r"AppData\Local\Programs\Microsoft VS Code\Code.exe"), r"C:\Program Files\Microsoft VS Code\Code.exe", "code"],
            "Android Studio": [r"C:\Program Files\Android\Android Studio\bin\studio64.exe"],
            "Arduino IDE": [str(user / r"AppData\Local\Programs\Arduino IDE\Arduino IDE.exe"), r"C:\Program Files\Arduino IDE\Arduino IDE.exe"],
            "Windows Terminal": ["wt"],
            "PowerShell": ["powershell"],
            "Command Prompt": ["cmd"],
            "Notepad": ["notepad"],
            "Calculator": ["calc"],
            "File Explorer": ["explorer"],
        }
        found = {}
        for name, candidates in known.items():
            path = self.find_first(candidates)
            if path:
                found[name] = path
        return found

    def find_first(self, candidates):
        for c in candidates:
            p = Path(os.path.expandvars(str(c)))
            if p.exists():
                return str(p)
            w = shutil.which(str(c)) or shutil.which(str(c) + ".exe")
            if w:
                return w
        return ""

    def default_browser(self):
        for b in ["Microsoft Edge", "Mozilla Firefox", "Google Chrome"]:
            if b in self.apps:
                return b
        return ""

    def resolve(self, name):
        q = " ".join(name.lower().split())
        smart = {
            "browser": self.default_browser(),
            "my browser": self.default_browser(),
            "default browser": self.default_browser(),
            "ide": "Android Studio" if "Android Studio" in self.apps else "Visual Studio Code",
            "my ide": "Android Studio" if "Android Studio" in self.apps else "Visual Studio Code",
            "code editor": "Visual Studio Code",
            "my code editor": "Visual Studio Code",
            "editor": "Visual Studio Code",
            "arduino": "Arduino IDE",
            "terminal": "Windows Terminal" if "Windows Terminal" in self.apps else "Command Prompt",
            "edge": "Microsoft Edge",
            "firefox": "Mozilla Firefox",
            "chrome": "Google Chrome",
            "vscode": "Visual Studio Code",
            "vs code": "Visual Studio Code",
        }
        if q in smart and smart[q] in self.apps:
            return smart[q]
        for app in self.apps:
            if app.lower() == q or q in app.lower():
                return app
        return None

    def open(self, target):
        websites = {"youtube":"https://youtube.com","github":"https://github.com","google":"https://google.com","gmail":"https://mail.google.com","chatgpt":"https://chatgpt.com"}
        q = target.lower().strip()
        if q in websites or "." in q:
            url = websites.get(q, target)
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return f"Opening {url}."
        app = self.resolve(target)
        if not app:
            return f"I could not find {target} on this PC."
        try:
            subprocess.Popen([self.apps[app]], shell=False)
            return f"Opening {app}."
        except Exception:
            try:
                os.startfile(self.apps[app])
                return f"Opening {app}."
            except Exception as exc:
                return f"Could not open {app}: {exc}"

    def status(self):
        return "Applications: " + ", ".join(sorted(self.apps.keys()))
