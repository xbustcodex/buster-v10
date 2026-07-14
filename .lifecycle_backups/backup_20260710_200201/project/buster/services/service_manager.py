class ServiceManager:
    def __init__(self, services, thread_pool):
        self.services = services
        self.thread_pool = thread_pool

    def status(self):
        lines = []
        for name, svc in sorted(self.services.all().items()):
            if name == "vision":
                lines.append(f"vision: {getattr(svc, 'state', 'loaded')}")
            else:
                lines.append(f"{name}: loaded")
        return "\n".join(lines)

    def diagnostics(self):
        return "Service Manager\n" + self.status() + "\n\n" + self.thread_pool.status()
