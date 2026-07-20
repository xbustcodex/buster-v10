"""
Buster Integration Hub - Lifecycle & Safety Engine

Handles lifecycle state transitions and validates safety guardrails:
- Confidence thresholds
- Destructive regression detection (dramatic size drop, dropped classes/functions)
- Protected file/directory policies
"""

from __future__ import annotations

import ast
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class HubState(Enum):
    IDLE = auto()
    DROPPED = auto()
    ANALYZING = auto()
    TARGET_DETECTED = auto()
    ROUTE_CONFIRMED = auto()
    SANITY_PASSED = auto()
    POLICY_APPROVED = auto()
    TRANSACTION_RUNNING = auto()
    COMMITTED = auto()
    FAILED_ROLLED_BACK = auto()


class SafetyValidator:
    """Evaluates patch risk based on structural deltas and protected routes."""

    PROTECTED_PATHS = {
        "buster/core/engine.py",
        "buster/runtime/kernel.py",
        "buster/core/integration/hub_lifecycle.py",
    }

    @classmethod
    def evaluate_safety(
        self,
        project_root: Path,
        target_rel_path: str,
        new_content: str,
        confidence: int,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Evaluates safety risk.
        Returns: (passed_all_policies, warning_flags, blocking_errors)
        """
        warnings: List[str] = []
        errors: List[str] = []

        target_path = project_root / target_rel_path

        # Guardrail 1: Low Confidence Warning
        if confidence < 75:
            warnings.append(f"Low routing confidence ({confidence}%). Verify target path carefully.")

        # Guardrail 2: Protected Path Check
        if target_rel_path in self.PROTECTED_PATHS:
            warnings.append("TARGET IS A PROTECTED KERNEL MODULE. Proceed with extreme caution.")

        # If target doesn't exist yet, it's a new creation (low structural risk)
        if not target_path.exists():
            return True, warnings, errors

        # Existing file regression checks
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                old_content = f.read()

            # Guardrail 3: Dramatic Size Reduction (>40% drop)
            old_size = len(old_content)
            new_size = len(new_content)
            if old_size > 0 and new_size < (old_size * 0.60):
                warnings.append(
                    f"Significant code reduction detected! Target drops from {old_size} to {new_size} bytes (-{int((1 - new_size/old_size)*100)}%)."
                )

            # Guardrail 4: Missing Symbols (Classes/Functions removed)
            old_tree = ast.parse(old_content)
            new_tree = ast.parse(new_content)

            old_classes = set(n.name for n in ast.walk(old_tree) if isinstance(n, ast.ClassDef))
            new_classes = set(n.name for n in ast.walk(new_tree) if isinstance(n, ast.ClassDef))
            missing_classes = old_classes - new_classes

            if missing_classes:
                warnings.append(f"Existing classes removed in this patch: {', '.join(missing_classes)}")

            old_funcs = set(n.name for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef))
            new_funcs = set(n.name for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef))
            missing_funcs = old_funcs - new_funcs

            if missing_funcs:
                warnings.append(f"Existing functions removed: {', '.join(missing_funcs)}")

        except Exception as exc:
            errors.append(f"AST Safety Analysis failed: {exc}")

        passed = len(errors) == 0
        return passed, warnings, errors