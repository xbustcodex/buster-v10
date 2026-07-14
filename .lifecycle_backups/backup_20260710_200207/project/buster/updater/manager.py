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
