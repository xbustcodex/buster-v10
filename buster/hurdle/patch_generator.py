from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.hurdle.classifier import Hurdle

logger = logging.getLogger(__name__)


@dataclass
class PatchCandidate:
    candidate_id: str
    hurdle_id: str
    target_path: str
    original_code: str
    proposed_code: str
    description: str
    is_valid_syntax: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatchGenerator:
    """Generates and preliminary-validates candidate patch code targeting reported Hurdles."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()

    def generate_candidate_patch(
        self,
        hurdle: Hurdle,
        replacement_code: Optional[str] = None,
        description: str = "Automated hurdle patch proposal",
    ) -> PatchCandidate:
        """Constructs a PatchCandidate and validates Python AST syntax before approval."""
        if not hurdle.file_path:
            raise ValueError("Cannot generate patch for hurdle without target file_path")

        file_path = Path(hurdle.file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        original_code = ""
        if file_path.exists():
            original_code = file_path.read_text(encoding="utf-8", errors="ignore")

        # If no custom replacement is provided, build a basic safe fallback candidate
        proposed_code = replacement_code if replacement_code is not None else original_code

        is_valid_syntax = self.validate_syntax(proposed_code)

        candidate_id = f"patch_{hash((hurdle.hurdle_id, proposed_code)) & 0xFFFFFF:06x}"

        return PatchCandidate(
            candidate_id=candidate_id,
            hurdle_id=hurdle.hurdle_id,
            target_path=str(hurdle.file_path),
            original_code=original_code,
            proposed_code=proposed_code,
            description=description,
            is_valid_syntax=is_valid_syntax,
        )

    @staticmethod
    def validate_syntax(code: str) -> bool:
        """Validates that proposed code parses into a clean Python AST without SyntaxError."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.warning(f"Syntax validation failed for patch candidate: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error validating code syntax: {e}")
            return False