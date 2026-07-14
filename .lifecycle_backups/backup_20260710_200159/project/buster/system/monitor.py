import psutil
import platform

class SystemMonitor:
    def snapshot(self):
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "os": platform.platform(),
            "cpu": int(psutil.cpu_percent(interval=None)),
            "ram": int(vm.percent),
            "disk": int(disk.percent),
            "processes": len(psutil.pids()),
        }

    def summary(self):
        s = self.snapshot()
        return f"CPU {s['cpu']} percent. RAM {s['ram']} percent. Disk {s['disk']} percent. Processes {s['processes']}."
