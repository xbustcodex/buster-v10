import fnmatch
import hashlib
import os
from pathlib import Path


class LifecycleScanner:
    def __init__(self, root: Path, exclude_patterns=None):
        self.root = Path(root)
        self.exclude_patterns = exclude_patterns or []

    def should_exclude(self, rel_path: str) -> bool:
        rel_path = str(rel_path).replace("\\", "/")
        path_parts = rel_path.split("/")
        name = Path(rel_path).name

        for pattern in self.exclude_patterns:
            # Clean up leading/trailing slashes for evaluation consistency
            pattern = str(pattern).replace("\\", "/").strip().rstrip("/")

            if not pattern:
                continue

            # Check exact or wildcard matches on name and full relative path
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True

            if rel_path == pattern:
                return True

            # Check if the pattern is explicitly part of the parent folder hierarchy
            if pattern in path_parts:
                return True

            if rel_path.startswith(pattern + "/"):
                return True

        return False

    def hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def scan(self) -> dict:
        files = []
        hashes = {}
        total_size = 0

        for root, dirs, filenames in os.walk(self.root):
            root_path = Path(root)
            rel_root = root_path.relative_to(self.root).as_posix()

            dirs[:] = [
                d for d in dirs
                if not self.should_exclude(d if rel_root == "." else f"{rel_root}/{d}")
            ]

            for filename in filenames:
                file_path = root_path / filename
                rel_file = file_path.relative_to(self.root).as_posix()

                if self.should_exclude(rel_file):
                    continue

                try:
                    size = file_path.stat().st_size
                    file_hash = self.hash_file(file_path)
                except Exception:
                    continue

                files.append(rel_file)
                hashes[rel_file] = file_hash
                total_size += size

        return {
            "root": str(self.root),
            "files": files,
            "hashes": hashes,
            "size": total_size,
            "count": len(files)
        }
