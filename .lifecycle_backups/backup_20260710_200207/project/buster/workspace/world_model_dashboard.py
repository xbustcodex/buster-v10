from buster.world_model import WorldModelEngine

class WorldModelDashboard:
    def __init__(self, data_dir="data"):
        self.engine = WorldModelEngine(data_dir=data_dir)

    def snapshot(self):
        return self.engine.dashboard()
