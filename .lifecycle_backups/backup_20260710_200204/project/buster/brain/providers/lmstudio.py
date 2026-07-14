class LMStudioProvider:
    name = "lmstudio"

    def available(self):
        try:
            import requests
            r = requests.get("http://localhost:1234/v1/models", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def complete(self, prompt, context=""):
        try:
            import requests
            r = requests.post("http://localhost:1234/v1/chat/completions", json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "You are Buster, a desktop AI companion. Be direct."},
                    {"role": "user", "content": f"Context:\n{context}\n\nUser:\n{prompt}"},
                ],
                "temperature": 0.2,
            }, timeout=90)
            if r.status_code != 200:
                return f"LM Studio error: {r.status_code} {r.text[:200]}"
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            return f"LM Studio is not available: {exc}"

    def status(self):
        return f"lmstudio: {'ready' if self.available() else 'not running'}"
