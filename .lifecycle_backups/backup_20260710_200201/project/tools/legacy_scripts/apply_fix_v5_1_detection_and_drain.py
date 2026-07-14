from pathlib import Path

ROOT = Path(__file__).resolve().parent
REAL_LOOP = ROOT / "buster" / "perception" / "real_perception_loop.py"
VISION_FEED = ROOT / "buster" / "vision" / "perception_feed.py"

def patch_real_loop() -> None:
    text = REAL_LOOP.read_text(encoding="utf-8")

    if "    def drain_recent(" not in text:
        insert_at = text.find("    def tick(self) -> Dict[str, Any]:")
        method = '''    def drain_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        items = self.observations[-limit:]
        return list(items)

'''
        text = text[:insert_at] + method + text[insert_at:]

    REAL_LOOP.write_text(text, encoding="utf-8")

def patch_vision_feed() -> None:
    text = VISION_FEED.read_text(encoding="utf-8")

    if "    def feed_camera_detection(" not in text:
        insert_at = text.find("    def feed_observation")
        method = '''    def feed_camera_detection(
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
        text = text[:insert_at] + method + text[insert_at:]

    VISION_FEED.write_text(text, encoding="utf-8")

def main() -> None:
    print("=== Applying v5.1 Feed Detection + Drain Repair ===")
    patch_real_loop()
    patch_vision_feed()
    print(f"[WRITE] {REAL_LOOP.relative_to(ROOT)}")
    print(f"[WRITE] {VISION_FEED.relative_to(ROOT)}")
    print("\\nSUCCESS: feed_camera_detection and drain_recent repaired.")
    print("Next: python -m pytest")

if __name__ == "__main__":
    main()
