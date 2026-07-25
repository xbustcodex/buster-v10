from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class CodeAndIndexRunner:
    """Executes automated code maintenance and workspace indexing mission steps."""

    def execute_rebuild_index(self, workspace_root: str | Path, output_file: str = ".buster_index.json") -> Dict[str, Any]:
        """Scans workspace directory structure and outputs a fresh project index JSON."""
        root = Path(workspace_root)
        if not root.exists():
            return {"status": "failed", "error": f"Workspace root '{workspace_root}' does not exist."}

        files_indexed = []
        for p in root.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                files_indexed.append(str(p.relative_to(root)))

        index_data = {
            "root": str(root.resolve()),
            "total_files": len(files_indexed),
            "files": sorted(files_indexed),
        }

        target_path = root / output_file
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)

        return {
            "status": "success",
            "indexed_count": len(files_indexed),
            "index_path": str(target_path),
        }