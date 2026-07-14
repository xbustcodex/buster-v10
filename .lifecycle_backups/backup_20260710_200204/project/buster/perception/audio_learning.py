class AudioLearning:
    def __init__(self):
        self.phrases = {}

    def learn_phrase(self, phrase, meaning):
        key = phrase.strip().lower()
        self.phrases[key] = meaning
        return {"phrase": key, "meaning": meaning, "learned": True}

    def interpret(self, phrase):
        key = phrase.strip().lower()
        return self.phrases.get(key)
