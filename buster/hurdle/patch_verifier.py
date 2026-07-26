from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.hurdle.patch_generator import PatchCandidate

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    candidate_id: str
    target_path: str
    applied: bool
    tests_passed: bool
    rollback_performed: bool
    output: str
    issues: List[str] = field(default_factory=list)


class PatchVerifier:
    """Safely applies patch candidates, verifies them against test suites, and auto-rolls back on failure."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()

    def verify_and_apply(
        self,
        candidate: PatchCandidate,
        test_command: Optional[List[str]] = None,
    ) -> VerificationResult:
        """Applies patch, runs specified tests, and automatically rolls back if tests fail."""
        if not candidate.is_valid_syntax:
            return VerificationResult(
                candidate_id=candidate.candidate_id,
                target_path=candidate.target_path,
                applied=False,
                tests_passed=False,
                rollback_performed=False,
                output="Skipped execution due to syntax error in candidate patch.",
                issues=["Syntax error in proposed patch"],
            )

        file_path = Path(candidate.target_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        # Preserve original contents for backup/rollback
        backup_code = candidate.original_code
        if not backup_code and file_path.exists():
            backup_code = file_path.read_text(encoding="utf-8", errors="ignore")

        # 1. Apply Candidate Patch
        try:
            file_path.write_text(candidate.proposed_code, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write patch to {file_path}: {e}")
            return VerificationResult(
                candidate_id=candidate.candidate_id,
                target_path=candidate.target_path,
                applied=False,
                tests_passed=False,
                rollback_performed=False,
                output=f"Failed writing patch: {e}",
                issues=[str(e)],
            )

        # 2. Execute Verification Tests
        cmd = test_command or [sys.executable, "-m", "pytest", "-q"]
        tests_passed = False
        output = ""
        issues: List[str] = []

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = proc.stdout + "\n" + proc.stderr
            tests_passed = (proc.returncode == 0)
            if not tests_passed:
                issues.append(f"Verification command returned non-zero code {proc.returncode}")
        except subprocess.TimeoutExpired:
            output = "Verification command timed out after 30 seconds."
            issues.append("Test run timed out")
        except Exception as e:
            output = f"Execution error running verification: {e}"
            issues.append(str(e))

        # 3. Auto-Rollback if tests failed
        rollback_performed = False
        if not tests_passed:
            logger.warning(f"Patch {candidate.candidate_id} failed verification. Performing auto-rollback...")
            try:
                file_path.write_text(backup_code, encoding="utf-8")
                rollback_performed = True
            except Exception as e:
                logger.critical(f"CRITICAL: Rollback failed for {file_path}: {e}")
                issues.append(f"Rollback failed: {e}")

        return VerificationResult(
            candidate_id=candidate.candidate_id,
            target_path=candidate.target_path,
            applied=tests_passed,
            tests_passed=tests_passed,
            rollback_performed=rollback_performed,
            output=output,
            issues=issues,
        )