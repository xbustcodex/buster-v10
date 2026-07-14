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
