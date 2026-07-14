from __future__ import annotations

import json
from typing import Callable, Iterable

import requests


class OllamaStreamingClient:
    """
    Streaming helper for Ollama.

    This can be used by UI/voice code to show or speak partial output sooner.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host.rstrip("/")

    def stream_generate(self, model: str, prompt: str) -> Iterable[str]:
        response = requests.post(
            f"{self.host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True,
            timeout=90,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            data = json.loads(line.decode("utf-8"))
            chunk = data.get("response", "")
            if chunk:
                yield chunk

            if data.get("done"):
                break

    def collect(self, model: str, prompt: str, on_chunk: Callable[[str], None] | None = None) -> str:
        parts = []
        for chunk in self.stream_generate(model, prompt):
            parts.append(chunk)
            if on_chunk:
                on_chunk(chunk)
        return "".join(parts).strip()
