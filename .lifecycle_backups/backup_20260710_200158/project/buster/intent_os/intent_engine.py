from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List
import json

from buster.sdk import BusterSDK

from .activity_signals import ActivitySignal, ActivitySignalBuffer
from .intent_model import IntentHypothesis


class IntentActivityEngine:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.buffer = ActivitySignalBuffer()
        self.hypotheses: List[IntentHypothesis] = []
        self.state_file = self.data_dir / "intent_activity_state.json"
        self.hypotheses_file = self.data_dir / "intent_hypotheses.json"

    def add_signal(self, signal: ActivitySignal | Dict[str, Any]) -> ActivitySignal:
        if isinstance(signal, dict):
            signal = ActivitySignal(
                source=signal.get("source", "unknown"),
                type=signal.get("type", "activity"),
                summary=signal.get("summary", ""),
                confidence=float(signal.get("confidence", 0.7)),
                importance=float(signal.get("importance", 0.6)),
                data=dict(signal.get("data", {})),
            )
        self.buffer.add(signal)
        self.sdk.publish("intent.signal", signal.to_dict(), source="intent_engine")
        self._persist()
        return signal

    def add_workspace_events(self, events: Iterable[Dict[str, Any]]) -> None:
        for event in events:
            self.add_signal(event)

    def infer(self) -> IntentHypothesis:
        text = self.buffer.as_text()
        evidence: List[str] = []
        intent = "general_work"
        summary = "General computer activity detected."
        confidence = 0.45
        actions = ["observe quietly", "keep workspace context available"]

        if "android studio" in text or "gradle" in text or "adb" in text or "pixel" in text:
            intent = "android_development"
            summary = "Likely Android development session."
            confidence = 0.88
            evidence = self._evidence(["Android Studio", "Gradle", "ADB", "Pixel"])
            actions = [
                "load Android project context",
                "prepare tester agent",
                "monitor Git changes",
                "prepare Logcat workflow",
            ]

        if "esp32" in text or "arduino" in text or "platformio" in text:
            if intent == "android_development":
                intent = "hardware_android_development"
                summary = "Likely mixed Android and ESP32 hardware development session."
                confidence = 0.92
            else:
                intent = "esp32_development"
                summary = "Likely ESP32 or Arduino development session."
                confidence = 0.9
            evidence.extend(self._evidence(["ESP32", "Arduino", "PlatformIO"]))
            actions = [
                "load hardware project context",
                "prepare serial monitor workflow",
                "make ESP32 plugin available",
                "prepare build/test agents",
            ]

        if "pytest" in text or "failing" in text or "regression" in text or "test" in text:
            if confidence < 0.86:
                intent = "debugging_tests"
                summary = "Likely debugging or test repair session."
                confidence = 0.86
            evidence.extend(self._evidence(["pytest", "test", "regression", "failing"]))
            actions.append("prepare fixer agent")

        hypothesis = IntentHypothesis(
            intent=intent,
            summary=summary,
            confidence=min(confidence, 0.99),
            evidence=sorted(set(evidence)),
            recommended_actions=list(dict.fromkeys(actions)),
            risk="low" if confidence >= 0.75 else "medium",
        )
        self.hypotheses.append(hypothesis)
        self.sdk.publish("intent.hypothesis", hypothesis.to_dict(), source="intent_engine", priority="high" if hypothesis.confidence >= 0.85 else "normal")
        self._persist()
        return hypothesis

    def _evidence(self, terms: List[str]) -> List[str]:
        text = self.buffer.as_text()
        return [term for term in terms if term.lower() in text]

    def status(self) -> Dict[str, Any]:
        return {
            "signals": [s.to_dict() for s in self.buffer.recent(20)],
            "hypotheses": [h.to_dict() for h in self.hypotheses[-10:]],
            "last_hypothesis": self.hypotheses[-1].to_dict() if self.hypotheses else None,
        }

    def _persist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")
        self.hypotheses_file.write_text(json.dumps([h.to_dict() for h in self.hypotheses], indent=2), encoding="utf-8")
