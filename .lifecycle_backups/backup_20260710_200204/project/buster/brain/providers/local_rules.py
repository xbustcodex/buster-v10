class LocalRulesProvider:
    name = "local"

    def available(self):
        return True

    def complete(self, prompt, context=""):
        p = prompt.lower()
        if "what can you do" in p:
            return ("I can open apps, listen through the microphone, speak, remember, use webcam vision, "
                    "detect objects, learn faces, recognize faces, scan QR codes, control the desktop, "
                    "and delegate work to Builder, Tester, Fixer, Reviewer, and Verifier.")
        return "Local AI handled this. For deeper answers, switch to Ollama, LM Studio, or OpenRouter."

    def status(self):
        return "local: ready"
