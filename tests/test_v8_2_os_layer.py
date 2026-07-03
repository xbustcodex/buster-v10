from buster.os_layer.os_layer import OSLayer

def test_os_layer_roots():
    os_layer = OSLayer()
    result = os_layer.handle("os roots")
    assert "Approved folders" in result

def test_os_layer_unknown():
    os_layer = OSLayer()
    assert os_layer.handle("unknown command") is None
