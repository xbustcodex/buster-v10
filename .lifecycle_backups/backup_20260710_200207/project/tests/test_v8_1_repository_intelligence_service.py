from buster.repository.intelligence_service import RepositoryIntelligenceService

def test_repository_intelligence_service_summary():
    svc = RepositoryIntelligenceService(root=".")
    result = svc.summary()
    assert "Files:" in result

def test_repository_intelligence_service_index():
    svc = RepositoryIntelligenceService(root=".")
    result = svc.index()
    assert "Repository intelligence index rebuilt" in result
