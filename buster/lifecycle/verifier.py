import hashlib
import json
from pathlib import Path


class LifecycleVerifier:
    def __init__(self, root: Path):
        self.root = Path(root)

    def hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify_manifest(self, manifest: dict) -> dict:
        errors = []
        warnings = []

        for file_info in manifest.get("files", []):
            rel = file_info.get("path")
            expected_hash = file_info.get("hash")

            if not rel:
                continue

            path = self.root / rel

            if not path.exists():
                errors.append(f"Missing file: {rel}")
                continue

            if expected_hash:
                actual = self.hash_file(path)
                if actual != expected_hash:
                    errors.append(f"Hash mismatch: {rel}")

        return {
            "passed": not errors,
            "errors": errors,
            "warnings": warnings
        }

    def verify_config(self) -> dict:
        errors = []

        for rel in ["config/lifecycle_config.json", "version.json"]:
            path = self.root / rel
            if path.exists():
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception as e:
                    errors.append(f"Invalid JSON: {rel} - {e}")

        return {
            "passed": not errors,
            "errors": errors
        }
