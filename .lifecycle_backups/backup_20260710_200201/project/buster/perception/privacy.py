from dataclasses import dataclass

@dataclass
class PrivacyGate:
    mode: str = "companion"

    def allow_camera(self):
        return self.mode in {"companion", "development"}

    def allow_microphone(self):
        return self.mode in {"wake_word", "companion", "development"}

    def allow_screen(self):
        return self.mode in {"companion", "development"}

    def filter_observation(self, observation):
        source = observation.get("source", "")
        if source == "camera" and not self.allow_camera():
            return None
        if source == "microphone" and not self.allow_microphone():
            return None
        if source == "screen" and not self.allow_screen():
            return None
        return observation
