
from buster.ai_state.state import AIStateStore

def test_ai_state_report():
    store = AIStateStore(path="data/test_ai_os_state.json")
    store.update(mode="testing", current_project="buster")
    report = store.report()
    assert "Buster AI OS State" in report
    assert "testing" in report
