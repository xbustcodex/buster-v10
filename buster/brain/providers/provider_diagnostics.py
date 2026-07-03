from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from buster.brain.providers.ollama_models import OllamaModelManager


@dataclass
class ProviderDiagnostic:
    provider: str
    status: str
    details: Dict


class ProviderDiagnostics:
    """
    Diagnostics helper for AI provider status screens.
    """

    def ollama(self) -> ProviderDiagnostic:
        manager = OllamaModelManager()
        running = manager.is_running()
        models = manager.model_names() if running else []
        return ProviderDiagnostic(
            provider="ollama",
            status="ready" if running and models else ("running_no_models" if running else "not_running"),
            details={
                "running": running,
                "models": models,
                "selected_model": manager.choose_model(),
                "last_error": manager.last_error,
            },
        )

    def report(self) -> str:
        diag = self.ollama()
        lines = [
            "AI Provider Diagnostics",
            f"Ollama: {diag.status}",
            f"Selected model: {diag.details['selected_model']}",
            f"Installed models: {', '.join(diag.details['models']) or 'none'}",
        ]
        if diag.details.get("last_error"):
            lines.append(f"Last error: {diag.details['last_error']}")
        return "\n".join(lines)
