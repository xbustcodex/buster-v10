"""
Buster Patch Analyzer & Dry-Run Simulator

Provides dependency graph analysis, structural change deltas, 
and dry-run transaction simulation for incoming patches.
"""

from __future__ import annotations

import ast
import difflib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class PatchAnalyzer:
    """Analyzes structural impacts and simulates patch execution without writing to disk."""

    def __init__(self, project_root: Path, repo_index: Dict[str, Any]):
        self.project_root = project_root
        self.repo_index = repo_index

    def analyze_structural_delta(self, target_rel_path: str, new_content: str) -> Dict[str, Any]:
        """Calculates precise symbol additions, modifications, and removals."""
        target_file = self.project_root / target_rel_path
        
        if not target_file.exists():
            try:
                new_tree = ast.parse(new_content)
                new_classes = len([n for n in ast.walk(new_tree) if isinstance(n, ast.ClassDef)])
                new_funcs = len([n for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef)])
            except Exception:
                new_classes, new_funcs = 0, 0

            return {
                "is_existing": False,
                "added_classes": new_classes,
                "added_funcs": new_funcs,
                "modified_funcs": 0,
                "removed_funcs": 0,
                "new_imports": self._extract_imports(new_content),
            }

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                old_content = f.read()

            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)

            old_classes = {n.name for n in ast.walk(old_tree) if isinstance(n, ast.ClassDef)}
            new_classes = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.ClassDef)}

            old_funcs = {n.name for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef)}
            new_funcs = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef)}

            # Imports delta
            old_imports = set(self._extract_imports(old_content))
            new_imports = set(self._extract_imports(new_content))

            return {
                "is_existing": True,
                "added_classes": len(new_classes - old_classes),
                "added_funcs": len(new_funcs - old_funcs),
                "modified_funcs": len(old_funcs.intersection(new_funcs)),
                "removed_funcs": len(old_funcs - new_funcs),
                "new_imports": list(new_imports - old_imports),
            }
        except Exception:
            return {"is_existing": True, "error": "AST Delta Parse Failed"}

    def map_affected_components(self, target_rel_path: str, new_content: str) -> List[str]:
        """Identifies downstream system components affected by modifying this target file."""
        affected = [Path(target_rel_path).stem.replace("_", " ").title()]
        imports = self._extract_imports(new_content)

        # Trace module dependencies
        for imp in imports:
            if "dispatcher" in imp.lower():
                affected.append("Dispatcher")
            elif "runtime" in imp.lower():
                affected.append("Runtime Kernel")
            elif "audit" in imp.lower():
                affected.append("Audit Service")
            elif "agent" in imp.lower():
                affected.append("Agent Subsystem")

        # Map back to parent Mission Control UI
        if "ui" in target_rel_path:
            affected.append("Mission Control UI")

        return list(dict.fromkeys(affected))  # Unique preserve order

    def simulate_patch_transaction(self, target_rel_path: str, new_content: str) -> Dict[str, Any]:
        """Runs a complete dry-run transaction simulation with ZERO disk writes."""
        target_path = self.project_root / target_rel_path
        will_overwrite = target_path.exists()
        
        simulation = {
            "target_path": str(target_path),
            "will_create": not will_overwrite,
            "will_overwrite": will_overwrite,
            "rollback_available": True,
            "affected_files_count": 1,
            "required_restarts": [],
            "compile_check": "PASSED",
        }

        # Dry-run compilation check
        try:
            compile(new_content, filename=target_rel_path, mode="exec")
        except SyntaxError as e:
            simulation["compile_check"] = f"FAILED: Line {e.lineno} ({e.msg})"

        # Determine runtime service restarts
        if "ui" in target_rel_path:
            simulation["required_restarts"].append("Mission Control UI Panel Stack")
        if "runtime" in target_rel_path or "service" in target_rel_path:
            simulation["required_restarts"].append("Runtime Core Kernel Service")

        return simulation

    def _extract_imports(self, content: str) -> List[str]:
        try:
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            return imports
        except Exception:
            return []