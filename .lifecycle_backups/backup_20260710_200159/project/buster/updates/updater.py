import json
import urllib.request
from packaging import version

class UpdateChecker:
    def __init__(self, current_version, repo_url):
        self.current_version = current_version
        self.repo_url = repo_url.rstrip("/")

    def latest_release_api(self):
        return self.repo_url.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"

    def check(self):
        try:
            with urllib.request.urlopen(self.latest_release_api(), timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            latest = data.get("tag_name", "").lstrip("v")
            url = data.get("html_url", self.repo_url + "/releases")
            if latest and version.parse(latest) > version.parse(self.current_version):
                return True, latest, url
            return False, latest, url
        except Exception as exc:
            return False, None, str(exc)
