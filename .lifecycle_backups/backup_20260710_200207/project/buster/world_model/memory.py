class WorldMemory:
    def __init__(self):
        self.short_term = []
        self.episodic = []
        self.semantic = []

    def remember_short_term(self, item):
        self.short_term.append(item)
        self.short_term = self.short_term[-100:]
        return item

    def remember_episode(self, item):
        self.episodic.append(item)
        self.episodic = self.episodic[-500:]
        return item

    def remember_semantic(self, item):
        self.semantic.append(item)
        self.semantic = self.semantic[-500:]
        return item

    def snapshot(self):
        return {
            "short_term": list(self.short_term),
            "episodic": list(self.episodic),
            "semantic": list(self.semantic),
        }
