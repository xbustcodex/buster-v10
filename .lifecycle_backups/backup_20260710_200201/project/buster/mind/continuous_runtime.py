from __future__ import annotations
import threading, time
from typing import Callable, Dict, Any, List, Optional
from .cognitive_loop import CognitiveLoopEngine
ObservationProvider = Callable[[], List[Dict[str, Any]]]
class ContinuousMindRuntime:
    def __init__(self, loop: CognitiveLoopEngine | None = None, provider: ObservationProvider | None = None, interval: float = 5.0):
        self.loop=loop or CognitiveLoopEngine(); self.provider=provider or (lambda: []); self.interval=float(interval); self._running=False; self._thread: Optional[threading.Thread]=None
    def tick_once(self): return self.loop.tick(self.provider() or [])
    def start(self):
        if self._running: return
        self._running=True; self._thread=threading.Thread(target=self._run, name='BusterContinuousMind', daemon=True); self._thread.start()
    def _run(self):
        while self._running:
            try: self.tick_once()
            except Exception: pass
            time.sleep(self.interval)
    def stop(self):
        self._running=False
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=2.0)
    def is_running(self): return self._running
