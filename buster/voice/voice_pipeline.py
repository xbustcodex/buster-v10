from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class VoiceJob:
    text: str


class VoicePipeline:
    """
    Small threaded voice pipeline.

    Mic/listen code can push recognized text into submit().
    The AI worker handles responses without blocking the listener/UI.
    """

    def __init__(
        self,
        responder: Callable[[str], str],
        speaker: Optional[Callable[[str], None]] = None,
        on_response: Optional[Callable[[str, str], None]] = None,
    ):
        self.responder = responder
        self.speaker = speaker
        self.on_response = on_response
        self.jobs: queue.Queue[VoiceJob | None] = queue.Queue()
        self.thread: threading.Thread | None = None
        self.running = False

    def start(self):
        if self.running:
            return "Voice pipeline already running."
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        return "Voice pipeline started."

    def stop(self):
        if not self.running:
            return "Voice pipeline already stopped."
        self.running = False
        self.jobs.put(None)
        return "Voice pipeline stopped."

    def submit(self, text: str):
        if not self.running:
            self.start()
        self.jobs.put(VoiceJob(text=text))
        return "Voice job queued."

    def _worker(self):
        while self.running:
            job = self.jobs.get()
            if job is None:
                break

            try:
                reply = self.responder(job.text)
            except Exception as exc:
                reply = f"Voice pipeline error: {exc}"

            if self.on_response:
                self.on_response(job.text, reply)

            if self.speaker:
                try:
                    self.speaker(reply)
                except Exception:
                    pass
