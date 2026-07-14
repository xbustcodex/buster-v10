class WorkspaceDashboard:
    def __init__(self, services):
        self.services = services

    def report(self):
        lines = ["Buster Workspace"]
        for label, name, method in [
            ("AI", "ai", "quick_status"),
            ("Tasks", "tasks", "summary"),
            ("Repo", "repo", "status"),
            ("Voice", "voice", "status"),
            ("Vision", "vision", "status"),
        ]:
            try:
                value = getattr(self.services.get(name), method)()
                lines.append(label + ": " + str(value).replace("\n", " | ")[:180])
            except Exception:
                pass
        try:
            p = self.services.get("performance").snapshot()
            lines.append(f"Performance: CPU {p['system_cpu']}% RAM {p['process_ram_mb']}MB Threads {p['threads']}")
        except Exception:
            pass
        return "\n".join(lines)
