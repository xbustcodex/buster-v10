from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List, Optional

import requests


@dataclass
class OllamaModelInfo:
    name: str
    size: int | None = None
    modified_at: str = ""


class OllamaModelManager:
    """
    Detect installed Ollama models and choose a safe default.

    Priority:
    1. Preferred model, if installed.
    2. First installed coder model.
    3. First installed model.
    4. Fallback model name.
    """

    def __init__(self, host: str = "http://localhost:11434", fallback_model: str = "llama3.2"):
        self.host = host.rstrip("/")
        self.fallback_model = fallback_model
        self.last_error = ""

    def is_running(self) -> bool:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=1.5)
            return response.status_code == 200
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def list_models_api(self) -> List[OllamaModelInfo]:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=3)
            response.raise_for_status()
            data = response.json()
            models = []
            for item in data.get("models", []):
                name = item.get("name", "")
                if name:
                    models.append(OllamaModelInfo(
                        name=name,
                        size=item.get("size"),
                        modified_at=item.get("modified_at", ""),
                    ))
            return models
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def list_models_cli(self) -> List[OllamaModelInfo]:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = result.stdout.strip().splitlines()
            models = []
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    models.append(OllamaModelInfo(name=parts[0]))
            return models
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def list_models(self) -> List[OllamaModelInfo]:
        models = self.list_models_api()
        if models:
            return models
        return self.list_models_cli()

    def model_names(self) -> List[str]:
        return [model.name for model in self.list_models()]

    def choose_model(self, preferred: Optional[str] = None) -> str:
        names = self.model_names()

        if preferred and preferred in names:
            return preferred

        coder_models = [
            name for name in names
            if "coder" in name.lower() or "code" in name.lower()
        ]
        if coder_models:
            return coder_models[0]

        if names:
            return names[0]

        return preferred or self.fallback_model

    def status_text(self, active_model: Optional[str] = None) -> str:
        running = self.is_running()
        names = self.model_names() if running else []
        model = active_model or self.choose_model()

        if not running:
            return f"ollama: not running model={model} error={self.last_error}"

        if not names:
            return f"ollama: running but no models installed model={model}"

        return f"ollama: ready model={model} installed={', '.join(names)}"
