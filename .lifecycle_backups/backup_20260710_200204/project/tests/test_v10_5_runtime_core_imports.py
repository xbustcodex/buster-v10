def test_v10_5_runtime_core_imports():
    from buster.runtime import BusterRuntimeCore, create_runtime_core
    from buster.runtime.plugin_api import PluginHost

    assert BusterRuntimeCore is not None
    assert create_runtime_core is not None
    assert PluginHost is not None
