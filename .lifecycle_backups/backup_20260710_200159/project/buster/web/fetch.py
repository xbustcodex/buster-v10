from .models import WebPage
from .parser import html_to_text
from .permissions import WebPermissions
from .session import WebSession

class WebFetcher:
    def __init__(self, session: WebSession | None = None, permissions: WebPermissions | None = None):
        self.session = session or WebSession()
        self.permissions = permissions or WebPermissions()

    def fetch(self, url: str) -> WebPage:
        if not self.permissions.can_fetch_url(url):
            return WebPage(url=url, status_code=0, text="", metadata={"blocked": True})
        try:
            response = self.session.get(url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return WebPage(url=url, status_code=response.status_code, text="", metadata={
                    "content_type": content_type,
                    "skipped": "not_html",
                })
            title, text = html_to_text(response.text, self.permissions.max_chars_per_page)
            return WebPage(url=url, title=title, text=text, status_code=response.status_code,
                           metadata={"content_type": content_type})
        except Exception as exc:
            return WebPage(url=url, status_code=0, text="", metadata={"error": str(exc)})
