# buster/security/integrity.py
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Any, List


class SystemIntegrityMonitor:
    """Verifies core file hashes and runtime security posture for Buster."""

    def __init__(self, root_dir: str | Path = ".") -> None:
        self.root_dir = Path(root_dir)
        self.baselines: Dict[str, str] = {}

    def create_baseline(self, relative_paths: List[str]) -> Dict[str, str]:
        """Creates a secure hash baseline for specified relative paths."""
        self.baselines.clear()
        for rel_path in relative_paths:
            full_path = self.root_dir / rel_path
            if full_path.exists():
                sha256 = hashlib.sha256()
                sha256.update(full_path.read_bytes())
                self.baselines[rel_path] = sha256.hexdigest()
        return self.baselines

    def verify_integrity(self) -> Dict[str, Any]:
        """Verifies current file states against baseline hashes."""
        modified = []
        missing = []
        
        # If no baseline was explicitly created, seed default checks
        if not self.baselines:
            self.create_baseline(["buster/version.py", "buster/security/integrity.py"])

        for rel_path, expected_hash in self.baselines.items():
            full_path = self.root_dir / rel_path
            if not full_path.exists():
                missing.append(rel_path)
                continue
            
            sha256 = hashlib.sha256()
            try:
                sha256.update(full_path.read_bytes())
                if sha256.hexdigest() != expected_hash:
                    modified.append(rel_path)
            except Exception:
                modified.append(rel_path)

        is_secure = len(modified) == 0 and len(missing) == 0
        return {
            "secure": is_secure,
            "modified": modified,
            "missing": missing,
        }

    def get_integrity_report(self) -> Dict[str, Any]:
        """Runs baseline system security and integrity checks."""
        result = self.verify_integrity()
        return {
            "status": "secure" if result["secure"] else "compromised",
            "checked_paths_count": len(self.baselines),
            **result,
        }

# Alias for compatibility
SystemIntegrityChecker = SystemIntegrityMonitor