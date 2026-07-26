from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.learning.curiosity_scheduler import ExplorationTask

logger = logging.getLogger(__name__)


@dataclass
class ExplorationResult:
    task_id: str
    target_path: str
    success: bool
    summary: str
    issues_found: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CuriosityRunner:
    """Executes lightweight inspection and verification passes on curiosity exploration targets."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()

    def inspect_target(self, task: ExplorationTask) -> ExplorationResult:
        """Performs AST analysis and health checks on the specified file target."""
        file_path = self.project_root / task.target_path
        issues: List[str] = []

        if not file_path.exists():
            return ExplorationResult(
                task_id=task.task_id,
                target_path=task.target_path,
                success=False,
                summary="Target file does not exist",
                issues_found=["File missing"],
            )

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(file_path))

            # AST Analysis: count functions, classes, and check syntax
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            # Example simple static lint checks
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and len(node.body) > 50:
                    issues.append(f"Function '{node.name}' exceeds 50 lines")

            summary = (
                f"Explored {task.target_path}: found {len(classes)} classes, "
                f"{len(functions)} functions, {len(issues)} potential structural issues."
            )
            logger.info(summary)

            return ExplorationResult(
                task_id=task.task_id,
                target_path=task.target_path,
                success=True,
                summary=summary,
                issues_found=issues,
                metadata={
                    "class_count": len(classes),
                    "function_count": len(functions),
                    "curiosity_score": task.curiosity_score,
                },
            )

        except SyntaxError as e:
            msg = f"Syntax error in target: {e}"
            logger.warning(msg)
            return ExplorationResult(
                task_id=task.task_id,
                target_path=task.target_path,
                success=False,
                summary=msg,
                issues_found=[f"SyntaxError on line {e.lineno}"],
            )
        except Exception as e:
            msg = f"Failed to explore target: {e}"
            logger.exception(msg)
            return ExplorationResult(
                task_id=task.task_id,
                target_path=task.target_path,
                success=False,
                summary=msg,
                issues_found=[str(e)],
            )