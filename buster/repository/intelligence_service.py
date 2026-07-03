from buster.intelligence.project_intelligence import ProjectIntelligence

class RepositoryIntelligenceService:
    def __init__(self, root="."):
        self.root = root
        self.project = ProjectIntelligence(root=root)

    def index(self):
        index = self.project.build_index()
        return (
            "Repository intelligence index rebuilt.\n"
            f"Files: {len(index['files'])}\n"
            f"Classes: {len(index['classes'])}\n"
            f"Functions: {len(index['functions'])}\n"
            f"Imports: {len(index['imports'])}\n"
            f"TODOs: {len(index['todos'])}"
        )

    def summary(self):
        return self.project.ask("project summary")

    def todos(self):
        return self.project.ask("show todos")

    def where_is(self, query):
        return self.project.find_references(query)

    def find_symbol(self, name):
        return self.project.find_symbol(name)

    def find_references(self, query):
        return self.project.find_references(query)

    def imports_of(self, package):
        return self.project.find_imports_of(package)

    def changed_since_index(self):
        return self.project.changed_since_index()
