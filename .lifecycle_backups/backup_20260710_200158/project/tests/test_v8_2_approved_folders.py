from buster.os_layer.approved_folders import ApprovedFolders
from buster.os_layer.os_layer import OSLayer

def test_approved_folders_loads():
    folders = ApprovedFolders(path="data/test_approved_folders.json")
    assert isinstance(folders.load(), list)

def test_os_layer_roots():
    result = OSLayer().handle("approved folders")
    assert "Approved folders" in result
