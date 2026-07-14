class BusterPlugin:
    name = "Unnamed Plugin"
    version = "1.0.0"
    def status(self):
        return f"{self.name} v{self.version} loaded."
