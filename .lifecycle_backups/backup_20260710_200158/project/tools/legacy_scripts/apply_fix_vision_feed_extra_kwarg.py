from pathlib import Path

ROOT = Path(__file__).resolve().parent
VISION_FEED = ROOT / "buster" / "vision" / "perception_feed.py"

text = VISION_FEED.read_text(encoding="utf-8")

old = '''    def feed_camera_detection(
        self,
        label: str,
        confidence: float = 0.5,
        bbox: dict | None = None,
        importance: float = 0.6,
        data: dict | None = None,
    ) -> dict:
        payload = dict(data or {})
        payload.update({"label": label, "bbox": bbox or {}})
        return self.observe(
            observation_type="camera_detection",
            summary=f"Camera detected {label}",
            confidence=confidence,
            importance=importance,
            data=payload,
        )

'''

new = '''    def feed_camera_detection(
        self,
        label: str,
        confidence: float = 0.5,
        bbox: dict | None = None,
        importance: float = 0.6,
        data: dict | None = None,
        extra: dict | None = None,
        **kwargs,
    ) -> dict:
        payload = dict(data or {})
        payload.update(extra or {})
        payload.update(kwargs)
        payload.update({"label": label, "bbox": bbox or {}})
        return self.observe(
            observation_type="camera_detection",
            summary=f"Camera detected {label}",
            confidence=confidence,
            importance=importance,
            data=payload,
        )

'''

if old in text:
    text = text.replace(old, new)
else:
    # fallback: simple add **kwargs if patch shape changed
    text = text.replace("data: dict | None = None,\n    ) -> dict:", "data: dict | None = None,\n        extra: dict | None = None,\n        **kwargs,\n    ) -> dict:")
    text = text.replace("payload = dict(data or {})", "payload = dict(data or {})\n        payload.update(extra or {})\n        payload.update(kwargs)")

VISION_FEED.write_text(text, encoding="utf-8")
print("=== Applying VisionPerceptionFeed extra= Compatibility Repair ===")
print(f"[WRITE] {VISION_FEED.relative_to(ROOT)}")
print("\nSUCCESS: feed_camera_detection now accepts extra= and unknown kwargs.")
print("Next: python -m pytest")
