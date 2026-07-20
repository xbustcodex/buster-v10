"""
Buster Repository Knowledge Base & Auto-Router

Indexes project files by AST signatures, imports, and symbols.
Provides similarity matching, structural diffing, and confidence scoring.
"""

from __future__ import annotations

import ast
import difflib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("buster.integration.knowledge_base")


class RepoKnowledgeBase:
    """Indexes project structure and analyzes dropped code against known repository files."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.index: Dict[str, Dict[str, Any]] = {}
        self.learning_memory_path = self.project_root / ".buster" / "router_memory.json"
        self.learning_memory: Dict[str, str] = self._load_learning_memory()
        self.reindex()

    def _load_learning_memory(self) -> Dict[str, str]:
        if self.learning_memory_path.exists():
            try:
                with open(self.learning_memory_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load router learning memory: %s", e)
        return {}

    def save_learned_route(self, symbol_or_filename: str, rel_path: str) -> None:
        """Stores user corrections/confirmations to continuously train routing accuracy."""
        self.learning_memory[symbol_or_filename] = rel_path
        self.learning_memory_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.learning_memory_path, "w", encoding="utf-8") as f:
                json.dump(self.learning_memory, f, indent=2)
        except Exception as e:
            logger.error("Failed to save router learning memory: %s", e)

    def reindex(self) -> None:
        """Scans the repository and builds a structural AST index of existing Python files."""
        self.index.clear()
        for root, _, files in os.walk(self.project_root):
            rel_dir = Path(root).relative_to(self.project_root)
            # Skip hidden and cache folders
            if any(part.startswith(".") or part in {"__pycache__", "venv", "env"} for part in rel_dir.parts):
                continue

            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = str(rel_dir / file)
                    self._index_file(full_path, rel_path)

    def _index_file(self, full_path: Path, rel_path: str) -> None:
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            category = self._classify_category(rel_path, classes, imports)

            self.index[rel_path] = {
                "rel_path": rel_path,
                "filename": full_path.name,
                "classes": classes,
                "functions": functions,
                "imports": list(set(imports)),
                "category": category,
            }
        except Exception:
            pass

    def _classify_category(self, rel_path: str, classes: List[str], imports: List[str]) -> str:
        if "ui" in rel_path or any("PySide" in imp or "Qt" in imp for imp in imports):
            return "UI Panel"
        if "runtime" in rel_path or any("Audit" in c or "Dispatcher" in c for c in classes):
            return "Runtime"
        if "agents" in rel_path or any("Agent" in c for c in classes):
            return "Agent"
        if "plugins" in rel_path:
            return "Plugin"
        return "Core Module"

    def match_dropped_content(self, file_path: str) -> Dict[str, Any]:
        """Compares incoming dropped file against indexed repository to determine target location and confidence."""
        path_obj = Path(file_path)
        filename = path_obj.name

        # Check learning memory first
        if filename in self.learning_memory:
            target = self.learning_memory[filename]
            return {
                "target_rel_path": target,
                "confidence": 99,
                "category": self.index.get(target, {}).get("category", "Learned Module"),
                "matched_by": "Learning Memory",
                "is_existing": (self.project_root / target).exists(),
            }

        # Check exact filename match in index
        for rel_path, meta in self.index.items():
            if meta["filename"] == filename:
                return {
                    "target_rel_path": rel_path,
                    "confidence": 95,
                    "category": meta["category"],
                    "matched_by": "Exact Filename Index",
                    "is_existing": True,
                }

        # AST & Symbol Matching
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            dropped_classes = set(node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
            dropped_imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    dropped_imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dropped_imports.add(node.module)

            best_match: Optional[str] = None
            highest_score = 0.0

            for rel_path, meta in self.index.items():
                class_overlap = len(dropped_classes.intersection(set(meta["classes"])))
                import_overlap = len(dropped_imports.intersection(set(meta["imports"])))
                
                score = (class_overlap * 3.0) + (import_overlap * 1.0)
                if score > highest_score:
                    highest_score = score
                    best_match = rel_path

            if best_match and highest_score > 0:
                meta = self.index[best_match]
                confidence = min(90, int(70 + (highest_score * 5)))
                return {
                    "target_rel_path": best_match,
                    "confidence": confidence,
                    "category": meta["category"],
                    "matched_by": "AST Structural Overlap",
                    "is_existing": True,
                }

            # Fallback based on UI signatures
            if any("PySide" in imp or "QWidget" in content for imp in dropped_imports):
                target = f"buster/ui/v9/panels/{filename}"
                return {
                    "target_rel_path": target,
                    "confidence": 85,
                    "category": "UI Panel",
                    "matched_by": "AST Signature Rules",
                    "is_existing": (self.project_root / target).exists(),
                }

        except Exception:
            pass

        # Final default fallback
        target = f"buster/core/{filename}"
        return {
            "target_rel_path": target,
            "confidence": 60,
            "category": "Core Module",
            "matched_by": "Fallback Rule",
            "is_existing": (self.project_root / target).exists(),
        }

    def compute_diff_summary(self, new_content: str, target_rel_path: str) -> Dict[str, Any]:
        """Generates line counts and AST symbol differences between incoming code and existing target file."""
        target_file = self.project_root / target_rel_path
        if not target_file.exists():
            return {"is_new": True, "added_lines": len(new_content.splitlines()), "removed_lines": 0}

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                old_content = f.read()

            diff = list(difflib.unified_diff(old_content.splitlines(), new_content.splitlines()))
            added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
            removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

            # Symbol delta
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)

            old_classes = set(node.name for node in ast.walk(old_tree) if isinstance(node, ast.ClassDef))
            new_classes = set(node.name for node in ast.walk(new_tree) if isinstance(node, ast.ClassDef))

            return {
                "is_new": False,
                "added_lines": added,
                "removed_lines": removed,
                "new_classes": list(new_classes - old_classes),
                "unified_diff": "\n".join(diff[:100]),  # Preview cap
            }
        except Exception as e:
            return {"is_new": False, "error": str(e), "added_lines": 0, "removed_lines": 0}