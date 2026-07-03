from buster.intelligence.project_intelligence import ProjectIntelligence

def test_project_intelligence_builds_index():
    pi = ProjectIntelligence(root=".", output="data/test_project_index.json")
    index = pi.build_index()
    assert "files" in index
    assert "classes" in index
    assert "functions" in index
    assert len(index["files"]) > 0

def test_project_intelligence_answers_summary():
    pi = ProjectIntelligence(root=".", output="data/test_project_index.json")
    answer = pi.ask("project summary")
    assert "Files:" in answer
