import requests

class WebSession:
    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BusterDesktopCompanion/7.1 (+local-ai-agent)"
        })

    def get(self, url: str, **kwargs):
        timeout = kwargs.pop("timeout", self.timeout)
        return self.session.get(url, timeout=timeout, **kwargs)
