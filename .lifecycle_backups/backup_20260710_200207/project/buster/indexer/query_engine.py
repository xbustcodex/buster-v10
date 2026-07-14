class ProjectQueryEngine:
    def __init__(self, index):
        self.index = index

    def ask(self, question):
        q = question.lower()

        if "todo" in q:
            return self.index.get("todos", [])

        if "vision" in q:
            return [x for x in self.index.get("files", []) if "vision" in x.lower()]

        if "planner" in q:
            return [x for x in self.index.get("files", []) if "planner" in x.lower()]

        if "function" in q:
            return self.index.get("functions", [])

        if "class" in q:
            return self.index.get("classes", [])

        return self.index
