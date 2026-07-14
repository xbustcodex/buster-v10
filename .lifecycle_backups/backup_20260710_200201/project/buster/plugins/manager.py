class PluginManager:
    def __init__(self):
        self.plugins = ["Weather", "ESP32 Tools", "Arduino Tools", "Android Tools", "GitHub", "Ollama", "OpenRouter"]

    def load_builtin(self):
        return True

    def status(self):
        return "Plugins loaded: " + ", ".join(self.plugins)
