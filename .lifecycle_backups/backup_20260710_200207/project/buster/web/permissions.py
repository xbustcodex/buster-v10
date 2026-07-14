from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class WebPermissions:
    allow_internet: bool = True
    allow_fetch: bool = True
    max_pages_per_query: int = 3
    max_chars_per_page: int = 12000
    blocked_domains: tuple = ()
    allowed_schemes: tuple = ("http", "https")

    def can_search(self) -> bool:
        return self.allow_internet

    def can_fetch_url(self, url: str) -> bool:
        if not self.allow_internet or not self.allow_fetch:
            return False
        parsed = urlparse(url)
        if parsed.scheme not in self.allowed_schemes:
            return False
        domain = parsed.netloc.lower()
        return not any(domain.endswith(blocked.lower()) for blocked in self.blocked_domains)
