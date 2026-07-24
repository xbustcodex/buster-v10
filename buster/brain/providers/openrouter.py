import os

class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, model="openai/gpt-4o-mini"):
        self.model = model

    def available(self):
        return bool(os.environ.get("OPENROUTER_API_KEY"))

    def complete(self, prompt, context=""):
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            return "OpenRouter API key is missing. Set OPENROUTER_API_KEY and restart Buster."
        try:
            import requests
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are Buster, a desktop AI companion. Be direct."},
                        {"role": "user", "content": f"Context:\n{context}\n\nUser:\n{prompt}"},
                    ],
                    "max_tokens": 8192,
                    "max_completion_tokens": 8192,
                    "temperature": 0.2,
                },
                timeout=180)
            if r.status_code != 200:
                return f"OpenRouter error: {r.status_code} {r.text[:200]}"
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            return f"OpenRouter failed: {exc}"

    def status(self):
        return f"openrouter: {'ready' if self.available() else 'missing API key'} model={self.model}"