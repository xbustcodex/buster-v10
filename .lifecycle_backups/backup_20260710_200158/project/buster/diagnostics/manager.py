class DiagnosticsManager:
    def __init__(self, services):
        self.services = services

    def full_report(self):
        parts = [
            "Diagnostics",
            self.services.get("system").summary(),
            self.services.get("apps").status(),
            self.services.get("ai").quick_status(),
            self.services.get("plugins").status(),
            self.services.get("voice").status(),
            self.services.get("vision").status(),
            self.services.get("hardware").status(),
            self.services.get("thread_pool").status(),
        ]
        return "\n".join(parts)
