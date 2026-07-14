from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import subprocess
import sys


class V9LiveServices:
    def __init__(
        self,
        services=None,
        settings=None,
        runtime_core=None,
    ):
        self.services = services
        self.settings = settings
        self.runtime_core = runtime_core

    def safe(self, fn, fallback="unknown"):
        try:
            return fn()
        except Exception:
            return fallback

    def brain(self, text: str) -> str:
        text = str(text or "").strip()

        if not text:
            return "I am online."

        # Use the new shared runtime first.
        if self.runtime_core is not None:
            try:
                self.runtime_core.dispatcher.publish(
                    "chat.message.received",
                    {
                        "role": "user",
                        "text": text,
                    },
                    source="chat",
                )

                result = self.runtime_core.run(text)
                reply = self._format_runtime_result(result)

                self.runtime_core.dispatcher.publish(
                    "chat.message.completed",
                    {
                        "role": "assistant",
                        "request": text,
                        "text": reply,
                    },
                    source="chat",
                )

                return reply

            except Exception as exc:
                self.runtime_core.dispatcher.publish(
                    "chat.message.failed",
                    {
                        "request": text,
                        "error": str(exc),
                    },
                    source="chat",
                )

                return f"Runtime request failed: {exc}"

        # Legacy fallback.
        brain_service = self._legacy_service("brain")

        if brain_service is None:
            return "No brain or runtime service is connected."

        process = getattr(brain_service, "process", None)

        if not callable(process):
            return "The legacy brain service has no process() method."

        try:
            return str(process(text))
        except Exception as exc:
            return f"Brain service error: {exc}"

    def _legacy_service(self, name: str):
        if not self.services:
            return None

        try:
            return self.services.get(name)
        except (KeyError, TypeError, AttributeError):
            return None

    def _format_runtime_result(self, result: Any) -> str:
        if result is None:
            return "The runtime completed without returning a response."

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # Prefer useful human-readable fields.
            for key in (
                "message",
                "response",
                "output",
                "summary",
                "text",
            ):
                value = result.get(key)

                if isinstance(value, str) and value.strip():
                    return value

            # Planner/orchestrator results may contain a nested result.
            nested_result = result.get("result")

            if isinstance(nested_result, str):
                return nested_result

            if isinstance(nested_result, dict):
                for key in (
                    "message",
                    "response",
                    "output",
                    "summary",
                    "text",
                ):
                    value = nested_result.get(key)

                    if isinstance(value, str) and value.strip():
                        return value

            try:
                return json.dumps(
                    result,
                    indent=2,
                    default=str,
                )
            except Exception:
                return str(result)

        return str(result)

    def git_branch(self):
        result = subprocess.run(
            "git branch --show-current",
            capture_output=True,
            text=True,
            shell=True,
        )
        return result.stdout.strip() or "unknown"

    def python_version(self):
        return sys.version.split()[0]

    def quick_info(self):
        ai_service = self._legacy_service("ai")

        if ai_service is not None:
            ai = self.safe(
                lambda: ai_service.quick_status(),
                "unknown",
            )
        elif self.runtime_core is not None:
            ai = "Runtime Connected"
        else:
            ai = "Not Connected"

        return (
            "QUICK INFO\n\n"
            f"AI Provider      {ai}\n"
            f"Workspace        {Path.cwd().name}\n"
            f"Git Branch       {self.git_branch()}\n"
            f"Python           {self.python_version()}\n"
            "Internet         Connected\n\n"
            "● Buster v10 Connected Runtime"
        )