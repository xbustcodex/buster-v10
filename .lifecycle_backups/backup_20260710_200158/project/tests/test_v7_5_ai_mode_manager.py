from buster.brain.providers.ai_modes import AIModeManager
from buster.brain.providers.mode_detector import AIModeDetector
from buster.brain.providers.prompt_builder import PromptBuilder
from buster.brain.providers.provider_modes import ProviderModeController


def test_ai_mode_manager_voice_options():
    manager = AIModeManager()
    options = manager.options("voice")
    assert options["num_predict"] == 180
    assert options["temperature"] == 0.3
    assert manager.timeout("voice") == 120


def test_ai_mode_manager_coding_options_are_longer():
    manager = AIModeManager()
    assert manager.options("coding")["num_predict"] > manager.options("voice")["num_predict"]


def test_prompt_builder_uses_voice_prompt():
    prompt = PromptBuilder().build("hello", mode="voice")
    assert "voice conversations" in prompt
    assert "User:\nhello" in prompt


def test_mode_detector_voice_default():
    detector = AIModeDetector()
    assert detector.detect("how are you", voice=True) == "voice"


def test_mode_detector_coding():
    detector = AIModeDetector()
    assert detector.detect("fix this pytest error") == "coding"


def test_mode_detector_research():
    detector = AIModeDetector()
    assert detector.detect("research latest android studio docs") == "research"


def test_provider_mode_controller_set_and_status():
    controller = ProviderModeController()
    assert controller.set_mode("voice") == "AI mode set to voice."
    assert "AI mode: voice" in controller.status()
