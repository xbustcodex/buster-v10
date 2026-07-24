import json
import time
from pathlib import Path
from buster.brain.providers.local_rules import LocalRulesProvider
from buster.brain.providers.ollama import OllamaProvider
from buster.brain.providers.lmstudio import LMStudioProvider
from buster.brain.providers.openrouter import OpenRouterProvider


class AIProviderManager:
    def __init__(self, config_file):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.providers = {
            "local": LocalRulesProvider(),
            "ollama": OllamaProvider(),
            "lmstudio": LMStudioProvider(),
            "openrouter": OpenRouterProvider(),
        }
        self.current = "ollama"
        self._cached_status = "AI provider starting..."
        self._last_status_check = 0.0
        self._status_ttl = 15.0
        self.load()

    def load(self):
        if not self.config_file.exists():
            self.save()
            return
        try:
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
            self.current = data.get("current", "ollama")
            if self.current not in self.providers:
                self.current = "ollama"
        except Exception:
            self.current = "ollama"

    def save(self):
        self.config_file.write_text(
            json.dumps({"current": self.current}, indent=2), encoding="utf-8"
        )

    def set_provider(self, name):
        key = name.lower().replace(" ", "")
        aliases = {
            "lm": "lmstudio",
            "lmstudio": "lmstudio",
            "local": "local",
            "ollama": "ollama",
            "openrouter": "openrouter",
        }
        key = aliases.get(key, key)
        if key not in self.providers:
            return f"Unknown AI provider: {name}"
        self.current = key
        self.save()
        self._last_status_check = 0
        return f"AI provider set to {key}. {self.quick_status()}"

    def complete(self, prompt, context=""):
        provider = self.providers.get(self.current, self.providers["local"])

        # Give active provider a short pause if warming up instead of collapsing to local rules
        if self.current != "local" and not provider.available():
            time.sleep(2.0)
            if not provider.available():
                return f"Error: Provider '{self.current}' is not available ({provider.status()})."

        return provider.complete(prompt, context)

    def quick_status(self):
        return f"Current: {self.current}"

    def status(self):
        now = time.time()
        if now - self._last_status_check < self._status_ttl:
            return self._cached_status
        lines = [f"Current AI provider: {self.current}"]
        for name, provider in self.providers.items():
            try:
                lines.append(provider.status())
            except Exception as exc:
                lines.append(f"{name}: error {exc}")
        self._cached_status = "\n".join(lines)
        self._last_status_check = now
        return self._cached_status

    def current_provider(self):
        return self.current

    def current_model(self):
        provider = self.providers.get(self.current)

        if provider is None:
            return "Unknown"

        return getattr(provider, "model", "Unknown")