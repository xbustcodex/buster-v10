import time
import threading
import psutil

class PerformanceMonitor:
    def __init__(self, services=None, thread_pool=None):
        self.services = services
        self.thread_pool = thread_pool
        self.started = time.time()

    def snapshot(self):
        proc = psutil.Process()
        mem = proc.memory_info()
        return {
            "uptime_sec": int(time.time() - self.started),
            "process_cpu": proc.cpu_percent(interval=None),
            "process_ram_mb": round(mem.rss / (1024 * 1024), 1),
            "system_cpu": int(psutil.cpu_percent(interval=None)),
            "system_ram": int(psutil.virtual_memory().percent),
            "threads": threading.active_count(),
            "vision_fps": self._vision_fps(),
            "thread_pool": self.thread_pool.status() if self.thread_pool else "No pool",
        }

    def _vision_fps(self):
        try:
            if self.services and self.services.has("vision"):
                return round(float(self.services.get("vision").fps), 1)
        except Exception:
            pass
        return 0.0

    def report(self):
        s = self.snapshot()
        return (
            "Performance\n"
            f"Uptime: {s['uptime_sec']} sec\n"
            f"Process CPU: {s['process_cpu']}%\n"
            f"Process RAM: {s['process_ram_mb']} MB\n"
            f"System CPU: {s['system_cpu']}%\n"
            f"System RAM: {s['system_ram']}%\n"
            f"Threads: {s['threads']}\n"
            f"Vision FPS: {s['vision_fps']}\n"
            f"{s['thread_pool']}"
        )
