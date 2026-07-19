from __future__ import annotations

import base64
from collections import defaultdict, Counter
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, List
from enum import Enum
import traceback
from PySide6.QtCore import QTimer
from .state_store import RuntimeStateStore
from threading import Event



from .storage import append_json, now

EVENTS_PATH = Path("data/runtime_events.json")

try:
    import numpy as np
except ImportError:
    np = None

def make_json_safe(value: Any) -> Any:
    """
    Recursively convert values into JSON-safe Python types.

    Supports:
    - NumPy scalars and arrays
    - pathlib.Path
    - datetime/date/time
    - Enum
    - dataclasses
    - dictionaries
    - lists, tuples and sets
    - bytes
    - objects exposing to_dict()
    """

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    # NumPy values
    if np is not None:
        if isinstance(value, np.ndarray):
            return make_json_safe(value.tolist())

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            numeric_value = float(value)

            # Avoid writing invalid JSON values such as NaN or Infinity.
            if np.isnan(numeric_value) or np.isinf(numeric_value):
                return None

            return numeric_value

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, np.generic):
            return make_json_safe(value.item())

    # Paths
    if isinstance(value, Path):
        return str(value)

    # Date and time values
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    # Enum members
    if isinstance(value, Enum):
        return make_json_safe(value.value)

    # Dataclasses
    if is_dataclass(value) and not isinstance(value, type):
        return make_json_safe(asdict(value))

    # Dictionaries
    if isinstance(value, dict):
        return {
            str(make_json_safe(key)): make_json_safe(item)
            for key, item in value.items()
        }

    # Lists and tuples
    if isinstance(value, (list, tuple)):
        return [
            make_json_safe(item)
            for item in value
        ]

    # Sets
    if isinstance(value, (set, frozenset)):
        return [
            make_json_safe(item)
            for item in value
        ]

    # Binary data
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {
            "__type__": "bytes",
            "encoding": "base64",
            "data": base64.b64encode(bytes(value)).decode("ascii"),
        }

    # Objects that provide their own dictionary representation
    to_dict = getattr(value, "to_dict", None)

    if callable(to_dict):
        try:
            return make_json_safe(to_dict())
        except Exception:
            pass

    # Plain Python objects
    object_dict = getattr(value, "__dict__", None)

    if isinstance(object_dict, dict):
        try:
            return make_json_safe(object_dict)
        except Exception:
            pass

    # Final safe fallback
    return str(value)

class RuntimeDispatcher:
    """
    Global Runtime Event Bus

    Supports:

        runtime.started
        runtime.stopped

        job.created
        job.started
        job.progress
        job.finished
        job.failed

        agent.started
        agent.finished

        face.state

        notification

        *

        runtime.*
        job.*
        face.*
    """

    def __init__(self, state_store=None):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[dict] = []
        self._stats = Counter()
        self.state = state_store or RuntimeStateStore()
        
        
        
    def _update_state(self, event: Dict[str, Any]) -> None:
        event_type = event["type"]
        payload = event.get("payload", {})

        self.state.set("last_event", event)

        if event_type in {"runtime.started", "runtime.core.started"}:
            self.state.update(
                "runtime",
                {
                    "started": True,
                    "status": "running",
                    "root": payload.get("root"),
                },
            )

        elif event_type in {"runtime.stopped", "runtime.core.stopped"}:
            self.state.update(
                "runtime",
                {
                    "started": False,
                    "status": "stopped",
                },
            )

        elif event_type == "runtime.tick":
            self.state.update(
                "runtime",
                {
                    "last_tick": event.get("created_at"),
                    "tick": payload,
                },
            )

        elif event_type == "job.created":
            jobs = self.state.get("jobs", {})
            items = list(jobs.get("jobs", []))
            items.append(payload)

            self.state.update(
                "jobs",
                {
                    "jobs": items,
                    "count": len(items),
                },
            )

        elif event_type in {"job.started", "job.progress"}:
            counts = self.state.get("jobs", {}).get("counts", {})
            counts["running"] = max(1, int(counts.get("running", 0)))

            self.state.update(
                "jobs",
                {
                    "counts": counts,
                    "active": payload,
                },
            )

            self.state.update(
                "face",
                {
                    "state": "working",
                    "message": payload.get("title")
                    or payload.get("job")
                    or "A runtime job is running.",
                },
            )

        elif event_type == "job.finished":
            counts = self.state.get("jobs", {}).get("counts", {})
            counts["running"] = max(0, int(counts.get("running", 0)) - 1)
            counts["completed"] = int(counts.get("completed", 0)) + 1

            self.state.update(
                "jobs",
                {
                    "counts": counts,
                    "active": None,
                    "last_finished": payload,
                },
            )

            self.state.update(
                "face",
                {
                    "state": "success",
                    "message": "The runtime job completed successfully.",
                },
            )

        elif event_type == "job.failed":
            counts = self.state.get("jobs", {}).get("counts", {})
            counts["running"] = max(0, int(counts.get("running", 0)) - 1)
            counts["failed"] = int(counts.get("failed", 0)) + 1

            self.state.update(
                "jobs",
                {
                    "counts": counts,
                    "active": None,
                    "last_failed": payload,
                },
            )

            self.state.update(
                "face",
                {
                    "state": "error",
                    "message": payload.get("error", "A runtime job failed."),
                },
            )

        elif event_type == "agent.started":
            agent = str(payload.get("agent", "unknown"))
            active = self.state.get("agents", {}).get("active", {})
            active[agent] = "running"

            self.state.update(
                "agents",
                {
                    "active": active,
                },
            )

            face_state = "thinking" if agent == "planner" else "working"

            self.state.update(
                "face",
                {
                    "state": face_state,
                    "message": f"{agent.title()} Agent is running.",
                },
            )

        elif event_type in {"agent.finished", "agent.failed"}:
            agent = str(payload.get("agent", "unknown"))
            active = self.state.get("agents", {}).get("active", {})
            active[agent] = (
                "failed" if event_type == "agent.failed" else "completed"
            )

            self.state.update(
                "agents",
                {
                    "active": active,
                    "last_result": payload,
                },
            )

        elif event_type == "face.state":
            self.state.update(
                "face",
                {
                    "state": payload.get("state", "idle"),
                    "message": payload.get("message", ""),
                },
            )

        elif event_type == "notification":
            self.state.set("notification", payload)

        elif event_type == "memory.updated":
            self.state.update("memory", payload)

        elif event_type == "workspace.changed":
            self.state.update("blackboard", {"workspace": payload})

        elif event_type == "voice.status":
            self.state.update("voice", payload)

        elif event_type == "vision.status":
            self.state.update("vision", payload)  

    def status(self):
        return {
            "subscribers": {
                key: len(value)
                for key, value in self.subscribers.items()
            },
            "history": len(self._history),
            "state": self.state.status(),
        }            

    # ----------------------------------------------------
    # Subscribe
    # ----------------------------------------------------

    def subscribe(self, event_type: str, handler):

        if handler not in self.subscribers[event_type]:
            self.subscribers[event_type].append(handler)

    # ----------------------------------------------------

    def unsubscribe(self, event_type: str, handler):

        if event_type not in self.subscribers:
            return

        try:
            self.subscribers[event_type].remove(handler)
        except ValueError:
            pass

    # ----------------------------------------------------

    def once(self, event_type: str, handler):

        def wrapper(event):

            self.unsubscribe(event_type, wrapper)

            QTimer.singleShot(
                0,
                lambda h=handler, e=event: h(e)
            )

        self.subscribe(event_type, wrapper)

    # ----------------------------------------------------
    # Publish
    # ----------------------------------------------------

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any] | None = None,
        source: str = "runtime",
    ):
        safe_payload = make_json_safe(payload or {})
        event = {
            "id": len(self._history) + 1,
            "type": str(event_type),
            "source": str(source),
            "payload": safe_payload,
            "created_at": make_json_safe(now()),
        }
       
        self._update_state(event)
        self._stats[event_type] += 1
        
        try:
            append_json(
                EVENTS_PATH,
                event,
                limit=1000,
            )
        except Exception as exc:
            print(
                f"[Dispatcher] Could not persist "
                f"event '{event_type}': {exc}"
            )
            
        self._history.append(event)
       

        if len(self._history) > 500:
            self._history.pop(0)

        append_json(EVENTS_PATH, event, limit=1000)

        handlers = []

        #
        # exact
        #

        handlers.extend(
            self.subscribers.get(event_type, [])
        )

        #
        # wildcard
        #

        parts = event_type.split(".")

        if len(parts) > 1:

            wildcard = parts[0] + ".*"

            handlers.extend(
                self.subscribers.get(wildcard, [])
            )

        #
        # global
        #

        handlers.extend(
            self.subscribers.get("*", [])
        )

        #
        # dispatch
        #

        for handler in handlers:

            try:
               # print(
               #     f"[Dispatcher] "
               #     f"{event_type} -> "
               #     f"{handler.__module__}.{handler.__qualname__}"
               # )

                handler(event)

            except Exception:
                print(
                    f"[Dispatcher] handler failed for '{event_type}'"
                )
                traceback.print_exc()

        return event

    # ----------------------------------------------------
    # Convenience
    # ----------------------------------------------------

    def notify(
        self,
        title,
        message,
        level="info",
    ):

        self.publish(
            "notification",
            {
                "title": title,
                "message": message,
                "level": level,
            },
        )

    # ----------------------------------------------------

    def face(
        self,
        state,
        message="",
    ):

        self.publish(
            "face.state",
            {
                "state": state,
                "message": message,
            },
        )

    # ----------------------------------------------------

    def job_progress(
        self,
        job,
        progress,
    ):

        self.publish(
            "job.progress",
            {
                "job": job,
                "progress": progress,
            },
        )

    # ----------------------------------------------------

    def history(self):

        return list(self._history)

    # ----------------------------------------------------

    def clear_history(self):

        self._history.clear()

    # ----------------------------------------------------

    def status(self):

        return {
            "subscribers": {
                k: len(v)
                for k, v in self.subscribers.items()
            },
            "history": len(self._history),
        }
        
    def statistics(self):

        return dict(self._stats)
        
    def wait_for(self, event_type, timeout=10):

        signal = Event()

        result = {}

        def listener(event):
            result["event"] = event
            signal.set()

        self.once(event_type, listener)

        signal.wait(timeout)

        return result.get("event")    