from concurrent.futures import ThreadPoolExecutor
import threading

class ThreadPool:
    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="BusterWorker")
        self.submitted = 0
        self.completed = 0
        self.failed = 0
        self.lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        with self.lock:
            self.submitted += 1

        future = self.executor.submit(fn, *args, **kwargs)

        def done_callback(f):
            with self.lock:
                if f.exception():
                    self.failed += 1
                else:
                    self.completed += 1

        future.add_done_callback(done_callback)
        return future

    def status(self) -> str:
        with self.lock:
            pending = max(0, self.submitted - self.completed - self.failed)
            return (
                f"ThreadPool workers={self.max_workers}, submitted={self.submitted}, "
                f"completed={self.completed}, failed={self.failed}, pending={pending}"
            )

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
