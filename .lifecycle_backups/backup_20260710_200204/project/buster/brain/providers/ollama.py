from __future__ import annotations

import requests

from buster.brain.providers.ai_modes import AIModeManager
from buster.brain.providers.ollama_models import OllamaModelManager
from buster.brain.providers.ollama_streaming import OllamaStreamingClient
from buster.brain.providers.prompt_builder import PromptBuilder


class OllamaProvider:
    name = "ollama"

    def __init__(self, model=None, host: str = "http://localhost:11434", keep_alive: str = "10m"):
        self.host = host.rstrip("/")
        self.keep_alive = keep_alive
        self.mode_manager = AIModeManager()
        self.prompt_builder = PromptBuilder(self.mode_manager)
        self.model_manager = OllamaModelManager(host=self.host)
        self.streaming = OllamaStreamingClient(host=self.host)
        self.preferred_model = model
        self.model = self.model_manager.choose_model(model)
        self.last_error = ""

    def set_mode(self, mode: str):
        return self.mode_manager.set_mode(mode)

    def refresh_model(self):
        self.model = self.model_manager.choose_model(self.preferred_model)
        return self.model

    def available(self):
        return self.model_manager.is_running()

    def warmup(self):
        self.refresh_model()
        try:
            requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "ready",
                    "stream": False,
                    "keep_alive": self.keep_alive,
                    "options": {"num_predict": 1},
                },
                timeout=30,
            )
            return f"Ollama model warmed: {self.model}"
        except Exception as exc:
            self.last_error = str(exc)
            return f"Ollama warmup failed: {exc}"

    def complete(self, prompt, context="", mode: str | None = None):
        self.refresh_model()
        selected_mode = self.mode_manager.get_mode(mode)

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "keep_alive": self.keep_alive,
                    "options": self.mode_manager.options(selected_mode.name),
                    "prompt": self.prompt_builder.build(prompt, context, selected_mode.name),
                    "stream": False,
                },
                timeout=self.mode_manager.timeout(selected_mode.name),
            )

            if response.status_code == 404:
                installed = ", ".join(self.model_manager.model_names()) or "none"
                return (
                    f"Ollama model not found: {self.model}. "
                    f"Installed models: {installed}. "
                    "Run `ollama pull <model>` or change the preferred model."
                )

            if response.status_code != 200:
                return f"Ollama error: {response.status_code} {response.text[:200]}"

            return response.json().get("response", "").strip() or "Ollama returned no text."

        except Exception as exc:
            self.last_error = str(exc)
            return f"Ollama is not available: {exc}"

    def complete_stream(self, prompt, context="", on_chunk=None, mode: str | None = None):
        self.refresh_model()
        selected_mode = self.mode_manager.get_mode(mode)
        try:
            return self.streaming.collect(
                self.model,
                self.prompt_builder.build(prompt, context, selected_mode.name),
                on_chunk=on_chunk,
            )
        except Exception as exc:
            self.last_error = str(exc)
            return f"Ollama streaming is not available: {exc}"

    def status(self):
        self.refresh_model()
        return self.model_manager.status_text(self.model) + f" mode={self.mode_manager.get_mode().name}"
