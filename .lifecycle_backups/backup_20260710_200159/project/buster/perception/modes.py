from dataclasses import dataclass

PERCEPTION_MODES = {
    "off": {"camera": False, "microphone": False, "screen": False, "description": "No active sensing."},
    "wake_word": {"camera": False, "microphone": True, "screen": False, "description": "Listen only for wake activation."},
    "companion": {"camera": True, "microphone": True, "screen": True, "description": "Ambient local awareness for useful companion behaviour."},
    "development": {"camera": True, "microphone": True, "screen": True, "description": "Focus on IDEs, terminals, builds, devices, and project context."},
    "privacy": {"camera": False, "microphone": False, "screen": False, "description": "Temporarily pause observation while keeping Buster running."},
}

@dataclass
class PerceptionMode:
    name: str = "companion"

    def config(self):
        return PERCEPTION_MODES.get(self.name, PERCEPTION_MODES["companion"])

    def allows(self, sense: str) -> bool:
        return bool(self.config().get(sense, False))
