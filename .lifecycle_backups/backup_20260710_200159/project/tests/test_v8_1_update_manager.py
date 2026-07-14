from buster.updater.version import clean_version, is_newer

def test_clean_version():
    assert clean_version("v8.1.0") == "8.1.0"

def test_is_newer():
    assert is_newer("8.2.0", "8.1.0")
    assert not is_newer("8.1.0", "8.1.0")
