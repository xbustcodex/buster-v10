from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    WAKE_DETECTED = "wake_detected"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"


class VoiceStateMachine:
    """Single runtime source of truth for Buster's voice state."""

    def __init__(self, runtime_core: Any):
        self.runtime_core = runtime_core
        self.dispatcher = getattr(runtime_core, "dispatcher", None)

        self._state = VoiceState.IDLE
        self._previous_state = VoiceState.IDLE
        self._reason = "initial"
        self._changed_at = time.time()

        self._lock = threading.RLock()
        self._subscriptions = []

        self._subscribe_events()

    @property
    def state(self) -> VoiceState:
        with self._lock:
            return self._state

    @property
    def running(self) -> bool:
        return True

    @property
    def configured(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return True

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self._state.value,
                "state": self._state.value,
                "previous_state": self._previous_state.value,
                "reason": self._reason,
                "changed_at": self._changed_at,
                "running": True,
                "configured": True,
                "available": True,
            }

    def transition(
        self,
        target: VoiceState | str,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_state = (
            target
            if isinstance(target, VoiceState)
            else VoiceState(str(target))
        )

        with self._lock:
            current = self._state
            if current == target_state:
                return self.status()

            self._previous_state = current
            self._state = target_state
            self._reason = reason or f"{current.value}->{target_state.value}"
            self._changed_at = time.time()

            payload = {
                "state": target_state.value,
                "previous_state": current.value,
                "reason": self._reason,
                "changed_at": self._changed_at,
                **(metadata or {}),
            }

        self._publish("voice.state.changed", payload)
        self._publish(f"voice.{target_state.value}", payload)
        return self.status()

    def reset(self, *, reason: str = "manual_reset") -> dict[str, Any]:
        return self.transition(
            VoiceState.IDLE,
            reason=reason,
        )

    def _subscribe_events(self) -> None:
        subscribe = getattr(self.dispatcher, "subscribe", None)
        if not callable(subscribe):
            return

        handlers = {
            "audio.streaming.started": lambda _event: self.transition(
                VoiceState.LISTENING,
                reason="streaming_started",
            ),
            "audio.streaming.stopped": lambda _event: self.transition(
                VoiceState.IDLE,
                reason="streaming_stopped",
            ),
            "audio.wake_word.detected": lambda _event: self.transition(
                VoiceState.WAKE_DETECTED,
                reason="wake_word_detected",
            ),
            "audio.wake_word.awaiting_command": lambda _event: self.transition(
                VoiceState.LISTENING,
                reason="awaiting_command",
            ),
            "audio.wake_word.command": lambda _event: self.transition(
                VoiceState.THINKING,
                reason="voice_command_received",
            ),
            "audio.tts.started": lambda _event: self.transition(
                VoiceState.SPEAKING,
                reason="tts_started",
            ),
            "audio.tts.completed": lambda _event: self.transition(
                VoiceState.LISTENING,
                reason="tts_completed",
            ),
            "audio.tts.interrupted": lambda _event: self.transition(
                VoiceState.INTERRUPTED,
                reason="tts_interrupted",
            ),
            "audio.error": lambda _event: self.transition(
                VoiceState.ERROR,
                reason="audio_error",
            ),
            "voice.state.reset.requested": lambda _event: self.reset(),
        }

        for topic, handler in handlers.items():
            try:
                unsubscribe = subscribe(topic, handler)
                if callable(unsubscribe):
                    self._subscriptions.append(unsubscribe)
            except Exception:
                continue

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        publish = getattr(self.dispatcher, "publish", None)
        if not callable(publish):
            return

        try:
            publish(
                topic,
                payload,
                source="voice_state_machine",
            )
        except TypeError:
            publish(topic, payload)
