from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from buster.hurdle.classifier import Hurdle, HurdleClassifier
from buster.hurdle.patch_generator import PatchCandidate, PatchGenerator
from buster.hurdle.patch_verifier import PatchVerifier, VerificationResult

logger = logging.getLogger(__name__)


class HurdleEngine:
    """Orchestrates hurdle classification, patch generation, and sandboxed verification."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.classifier = HurdleClassifier(project_root=self.project_root)
        self.generator = PatchGenerator(project_root=self.project_root)
        self.verifier = PatchVerifier(project_root=self.project_root)

    def process_exception(
        self,
        exc: Exception,
        replacement_code: Optional[str] = None,
        test_command: Optional[list[str]] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> VerificationResult:
        """Classifies an exception into a hurdle, generates a patch, and verifies it."""
        hurdle = self.classifier.classify_exception(
            exc=exc,
            file_path=file_path,
            line_number=line_number,
        )

        candidate = self.generator.generate_candidate_patch(
            hurdle=hurdle,
            replacement_code=replacement_code,
            description=f"Auto-generated patch for {hurdle.error_type}",
        )

        return self.verifier.verify_and_apply(
            candidate=candidate,
            test_command=test_command,
        )