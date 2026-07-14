from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VoiceLatencyConfig:
    """
    Fast voice settings.

    timeout:
        How long Buster waits for speech to start.
    phrase_time_limit:
        Max seconds for one spoken command.
    pause_threshold:
        How much silence counts as the user finishing.
    non_speaking_duration:
        Amount of silence kept around phrases.
    dynamic_energy_threshold:
        Lets SpeechRecognition adapt to room noise.
    """

    timeout: float = 2.0
    phrase_time_limit: float = 6.0
    pause_threshold: float = 0.55
    non_speaking_duration: float = 0.25
    dynamic_energy_threshold: bool = True
    energy_threshold: int | None = None

    def apply_to_recognizer(self, recognizer):
        recognizer.pause_threshold = self.pause_threshold
        recognizer.non_speaking_duration = self.non_speaking_duration
        recognizer.dynamic_energy_threshold = self.dynamic_energy_threshold

        if self.energy_threshold is not None:
            recognizer.energy_threshold = self.energy_threshold

        return recognizer
