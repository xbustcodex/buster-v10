from buster.world_model import WorldModelEngine

class CompanionEngine:
    def __init__(self, data_dir="data", name="Adam"):
        self.world = WorldModelEngine(data_dir=data_dir)
        self.name = name

    def morning_message(self):
        status = self.world.understand_now()
        mode = status.get("context", {}).get("mode", "idle")
        if mode == "android_development":
            return f"Good morning {self.name}. I can prepare Android monitoring when you are ready."
        if mode == "hardware_development":
            return f"Good morning {self.name}. I see hardware work may be active, so I can keep the device tools ready."
        return f"Good morning {self.name}. I'm online and watching for anything useful."

    def speak_from_world(self):
        status = self.world.understand_now()
        return status.get("recommendation", "I'm observing quietly.")
