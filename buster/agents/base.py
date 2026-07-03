class Agent:
    name = "base"

    def __init__(self, bus=None):
        self.bus = bus
        self.progress = 0
        self.status = "Ready"
        self.current_task = "Waiting"

    def run(self, task):
        self.current_task = task
        self.status = "Running"
        for p in [15, 35, 60, 85, 100]:
            self.progress = p
            if self.bus:
                self.bus.emit("agent_updated")
        self.status = "Done"
        return f"{self.name.title()} completed: {task}"
