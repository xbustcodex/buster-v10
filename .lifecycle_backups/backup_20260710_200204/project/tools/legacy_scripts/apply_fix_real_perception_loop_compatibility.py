from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "buster" / "perception" / "real_perception_loop.py"

text = TARGET.read_text(encoding="utf-8")

# Simple targeted compatibility patch.
text = text.replace('"text": text,', '"text": text,\n            "message": text,')

# Ensure observe returns legacy top-level keys.
old = """        result = {
            "ok": True,
            "observation": observation,
            "world_update": world_update,
            "companion_update": companion_update,
            "speech": speech,
            "state": dict(self.state),
        }"""
new = """        result = {
            "ok": True,
            "source": observation["source"],
            "type": observation["type"],
            "summary": observation["summary"],
            "confidence": observation["confidence"],
            "importance": observation["importance"],
            "observation": observation,
            "world_update": world_update,
            "companion_update": companion_update,
            "speech": speech,
            "state": dict(self.state),
        }"""
text = text.replace(old, new)

TARGET.write_text(text, encoding="utf-8")
print("=== Applying RealPerceptionLoop Compatibility Patch ===")
print(f"[WRITE] {TARGET.relative_to(ROOT)}")
print("\nSUCCESS: Legacy API compatibility restored.")
print("Next: python -m pytest")
