
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class V9LiveServices:
    PROVIDER_LABELS = {
        "openrouter": "OpenRouter",
        "ollama": "Ollama",
        "lmstudio": "LM Studio",
        "local": "Local Rules",
    }

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

        if self.runtime_core is not None:
            try:
                self.runtime_core.dispatcher.publish(
                    "chat.message.received",
                    {"role": "user", "text": text},
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
                try:
                    self.runtime_core.dispatcher.publish(
                        "chat.message.failed",
                        {
                            "request": text,
                            "error": str(exc),
                        },
                        source="chat",
                    )
                except Exception:
                    pass

                return f"Runtime request failed: {exc}"

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

            nested = result.get("result")
            if isinstance(nested, str):
                return nested

            if isinstance(nested, dict):
                for key in (
                    "message",
                    "response",
                    "output",
                    "summary",
                    "text",
                ):
                    value = nested.get(key)
                    if isinstance(value, str) and value.strip():
                        return value

            try:
                return json.dumps(result, indent=2, default=str)
            except Exception:
                return str(result)

        return str(result)

    def git_branch(self):
        try:
            result = subprocess.run(
                "git branch --show-current",
                capture_output=True,
                text=True,
                shell=True,
                timeout=3,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def python_version(self):
        return sys.version.split()[0]

    def ai_info(self):
        """
        Read AI configuration without calling provider.available() or status().

        This method is called by a repeating UI refresh. Network checks here would
        block the Qt event loop whenever Ollama, LM Studio, or another provider is
        not running.
        """
        info = {
            "provider": "unknown",
            "provider_label": "Unknown",
            "model": "Unknown",
            "connected": False,
            "status": "Unavailable",
        }

        manager = None

        if self.runtime_core is not None:
            manager = getattr(
                self.runtime_core,
                "ai_manager",
                None,
            )

            if manager is None:
                manager = getattr(
                    self.runtime_core,
                    "provider_manager",
                    None,
                )

        if manager is None:
            manager = self._legacy_service("ai")

        if manager is None:
            return info

        try:
            provider_key = str(
                getattr(manager, "current", "unknown")
            ).lower()

            provider = getattr(
                manager,
                "providers",
                {},
            ).get(provider_key)

            model = getattr(provider, "model", "Unknown")

            if provider is None:
                connected = False
                status = "Unavailable"
            elif provider_key == "local":
                connected = True
                status = "Ready"
            else:
                connected = None
                status = "Configured"

            info.update({
                "provider": provider_key,
                "provider_label": self.PROVIDER_LABELS.get(
                    provider_key,
                    provider_key.replace("_", " ").title(),
                ),
                "model": str(model or "Unknown"),
                "connected": connected,
                "status": status,
            })

        except Exception as exc:
            info["status"] = f"Error: {exc}"

        return info

    def quick_info(self):
        ai = self.ai_info()
        if ai["connected"] is True:
            connection_text = "Connected"
        elif ai["connected"] is False:
            connection_text = "Unavailable"
        else:
            connection_text = ai.get("status", "Configured")

        return (
            "QUICK INFO\n\n"
            f"AI Provider      {ai['provider_label']}\n"
            f"AI Model         {ai['model']}\n"
            f"AI Status        {connection_text}\n"
            f"Workspace        {Path.cwd().name}\n"
            f"Git Branch       {self.git_branch()}\n"
            f"Python           {self.python_version()}\n"
            "Internet         Connected\n\n"
            "● Buster v10 Connected Runtime"
        )
