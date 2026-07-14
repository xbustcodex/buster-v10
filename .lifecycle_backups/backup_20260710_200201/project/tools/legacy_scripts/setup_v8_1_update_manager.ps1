New-Item -ItemType Directory -Force "buster/updater" | Out-Null
New-Item -ItemType File -Force "buster/updater/__init__.py" | Out-Null

@'
from packaging import version

def clean_version(value):
    return str(value).strip().lower().lstrip("v")

def is_newer(latest, current):
    try:
        return version.parse(clean_version(latest)) > version.parse(clean_version(current))
    except Exception:
        return False
'@ | Set-Content "buster/updater/version.py"

@'
import json
import urllib.request

class GitHubReleaseClient:
    def __init__(self, repo="xbustcodex/buster-desktop-companion"):
        self.repo = repo

    def latest_url(self):
        return f"https://api.github.com/repos/{self.repo}/releases/latest"

    def latest_release(self):
        req = urllib.request.Request(
            self.latest_url(),
            headers={"User-Agent": "Buster-Update-Manager"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
'@ | Set-Content "buster/updater/github.py"

@'
from dataclasses import dataclass

@dataclass
class UpdateInfo:
    checked: bool
    available: bool
    current_version: str
    latest_version: str = ""
    release_url: str = ""
    release_name: str = ""
    error: str = ""
'@ | Set-Content "buster/updater/models.py"

@'
from buster.updater.github import GitHubReleaseClient
from buster.updater.models import UpdateInfo
from buster.updater.version import is_newer

class UpdateManager:
    def __init__(self, current_version, repo="xbustcodex/buster-desktop-companion"):
        self.current_version = current_version
        self.client = GitHubReleaseClient(repo)

    def check(self):
        try:
            release = self.client.latest_release()
            latest = release.get("tag_name", "").lstrip("v")
            url = release.get("html_url", "")
            name = release.get("name", "")

            return UpdateInfo(
                checked=True,
                available=is_newer(latest, self.current_version),
                current_version=self.current_version,
                latest_version=latest,
                release_url=url,
                release_name=name,
            )
        except Exception as exc:
            return UpdateInfo(
                checked=False,
                available=False,
                current_version=self.current_version,
                error=str(exc),
            )

    def status_text(self):
        info = self.check()

        if not info.checked:
            return f"Update check failed:\n{info.error}"

        if info.available:
            return (
                "Update available.\n"
                f"Current: {info.current_version}\n"
                f"Latest: {info.latest_version}\n"
                f"Release: {info.release_name}\n"
                f"URL: {info.release_url}"
            )

        return (
            "Buster is up to date.\n"
            f"Current: {info.current_version}\n"
            f"Latest: {info.latest_version or 'unknown'}"
        )
'@ | Set-Content "buster/updater/manager.py"

@'
from buster.updater.version import clean_version, is_newer

def test_clean_version():
    assert clean_version("v8.1.0") == "8.1.0"

def test_is_newer():
    assert is_newer("8.2.0", "8.1.0")
    assert not is_newer("8.1.0", "8.1.0")
'@ | Set-Content "tests/test_v8_1_update_manager.py"

@'
from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

if "from buster.updater.manager import UpdateManager" not in text:
    text = text.replace(
        "from buster.repository.intelligence_service import RepositoryIntelligenceService\n",
        "from buster.repository.intelligence_service import RepositoryIntelligenceService\nfrom buster.updater.manager import UpdateManager\n",
        1
    )

needle = "        repo_intel = RepositoryIntelligenceService(root=\".\")\n"

commands = '''        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(
                current_version=getattr(self.services.get("settings"), "version", "8.1.0")
                if hasattr(self, "services") else "8.1.0"
            ).status_text()

'''

if "UpdateManager(" not in text:
    text = text.replace(needle, commands + needle, 1)

path.write_text(text, encoding="utf-8")
print("Update Manager command wired into BrainEngine.")
'@ | Set-Content "patch_update_manager.py"

python patch_update_manager.py

Write-Host "Update Manager installed."