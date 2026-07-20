"""
Buster Self-Improvement Protection Policy Engine v2.2

Pure evaluation engine for protection rules, risk scoring, path normalization, 
and policy state mapping without I/O or persistent side effects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple, Union


class FileClassification(Enum):
    NORMAL = auto()
    SENSITIVE = auto()
    CRITICAL = auto()


class DecisionStatus(Enum):
    APPROVED = auto()
    PENDING_APPROVAL = auto()
    BLOCKED = auto()


@dataclass(frozen=True)
class ProtectionDecision:
    path: str
    classification: FileClassification
    status: DecisionStatus
    rule_name: str
    reason: str
    risk_score: int  # 0 to 100
    
    allow_review: bool
    allow_plan: bool
    allow_preview: bool
    allow_apply: bool
    requires_confirmation_phrase: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "classification": self.classification.name,
            "status": self.status.name,
            "rule_name": self.rule_name,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "permissions": {
                "allow_review": self.allow_review,
                "allow_plan": self.allow_plan,
                "allow_preview": self.allow_preview,
                "allow_apply": self.allow_apply,
                "requires_confirmation_phrase": self.requires_confirmation_phrase,
            },
        }


@dataclass
class ProtectionRule:
    name: str
    pattern: str
    classification: FileClassification
    reason: str
    risk_score: int = 0
    priority: int = 100
    is_directory: bool = False
    is_exact: bool = False

    def matches(self, normalized_path: str) -> bool:
        if self.is_exact:
            return normalized_path == self.pattern

        if self.is_directory:
            clean_pattern = self.pattern.rstrip("/")
            return (
                normalized_path == clean_pattern
                or normalized_path.startswith(f"{clean_pattern}/")
            )

        if self.pattern.startswith("*"):
            return normalized_path.endswith(self.pattern[1:])

        return normalized_path == self.pattern


class PathNormalizer:
    @staticmethod
    def normalize(
        path: Union[str, Path],
        project_root: Optional[Union[str, Path]] = None,
    ) -> str:
        if not path:
            return ""

        path_obj = Path(path)

        if project_root is not None:
            root_obj = Path(project_root).resolve()
            try:
                resolved_path = path_obj.resolve()
                if resolved_path.is_relative_to(root_obj):
                    path_obj = resolved_path.relative_to(root_obj)
            except (ValueError, RuntimeError):
                pass

        raw_posix = PurePosixPath(path_obj.as_posix()).as_posix()
        clean_path = raw_posix.lstrip("./").strip()

        if ":" in clean_path:
            clean_path = clean_path.split(":", 1)[-1].lstrip("/")

        return clean_path


class ProtectionPolicy:
    APPLY_DIR = "buster/ui/v9/panels/self_improvement/apply"

    DEFAULT_RULES: List[ProtectionRule] = [
        # --- Safety Suite Self-Preservation (CRITICAL / Priority 1000) ---
        ProtectionRule(
            name="protection_policy_immutable",
            pattern=f"{APPLY_DIR}/protection_policy.py",
            classification=FileClassification.CRITICAL,
            reason="Safety Engine: Policy authority code cannot modify itself.",
            risk_score=100,
            priority=1000,
            is_exact=True,
        ),
        ProtectionRule(
            name="patch_applier_immutable",
            pattern=f"{APPLY_DIR}/patch_applier.py",
            classification=FileClassification.CRITICAL,
            reason="Safety Engine: Patch execution engine is locked against self-modification.",
            risk_score=100,
            priority=1000,
            is_exact=True,
        ),
        ProtectionRule(
            name="sanity_validator_immutable",
            pattern=f"{APPLY_DIR}/sanity_validator.py",
            classification=FileClassification.CRITICAL,
            reason="Safety Engine: Pre-apply sanity validator is locked against self-modification.",
            risk_score=100,
            priority=1000,
            is_exact=True,
        ),
        ProtectionRule(
            name="protected_files_immutable",
            pattern=f"{APPLY_DIR}/protected_files.py",
            classification=FileClassification.CRITICAL,
            reason="Safety Engine: Protected files manifest is immutable.",
            risk_score=100,
            priority=1000,
            is_exact=True,
        ),

        # --- Core Runtime Infrastructure (CRITICAL / Priority 800) ---
        ProtectionRule(
            name="core_runtime_lock",
            pattern="buster/runtime/core.py",
            classification=FileClassification.CRITICAL,
            reason="Core Runtime Engine initializes system subservices and main bus.",
            risk_score=95,
            priority=800,
            is_exact=True,
        ),
        ProtectionRule(
            name="self_improvement_runtime_lock",
            pattern="buster/runtime/self_improvement_runtime.py",
            classification=FileClassification.CRITICAL,
            reason="Self-improvement authority runtime control loop.",
            risk_score=95,
            priority=800,
            is_exact=True,
        ),

        # --- Sensitive Directories & Entrypoints (SENSITIVE / Priority 500) ---
        ProtectionRule(
            name="runtime_directory",
            pattern="buster/runtime",
            classification=FileClassification.SENSITIVE,
            reason="Runtime infrastructure directory.",
            risk_score=80,
            priority=500,
            is_directory=True,
        ),
        ProtectionRule(
            name="core_directory",
            pattern="buster/core",
            classification=FileClassification.SENSITIVE,
            reason="Core business logic and bus architecture directory.",
            risk_score=80,
            priority=500,
            is_directory=True,
        ),
        ProtectionRule(
            name="plugins_directory",
            pattern="buster/plugins",
            classification=FileClassification.SENSITIVE,
            reason="System plugin subsystem directory.",
            risk_score=70,
            priority=500,
            is_directory=True,
        ),
        ProtectionRule(
            name="entrypoint_main",
            pattern="main.py",
            classification=FileClassification.SENSITIVE,
            reason="Primary application startup file.",
            risk_score=85,
            priority=500,
            is_exact=True,
        ),
        ProtectionRule(
            name="entrypoint_launcher",
            pattern="launcher.py",
            classification=FileClassification.SENSITIVE,
            reason="Application bootstrapper launcher.",
            risk_score=85,
            priority=500,
            is_exact=True,
        ),
    ]

    def __init__(
        self,
        project_root: Optional[Union[str, Path]] = None,
        custom_rules: Optional[List[ProtectionRule]] = None,
    ) -> None:
        self.project_root = Path(project_root).resolve() if project_root else None
        self._rules: List[ProtectionRule] = []

        if custom_rules:
            self._rules.extend(custom_rules)

        self._rules.extend(self.DEFAULT_RULES)
        self._sort_rules()

    def _sort_rules(self) -> None:
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self.clear_cache()

    def clear_cache(self) -> None:
        self._evaluate_cached.cache_clear()

    def evaluate(
        self,
        file_path: Union[str, Path],
        user_approved: bool = False,
    ) -> ProtectionDecision:
        """Evaluates path purely against rules, returning a decision state object."""
        norm_path = PathNormalizer.normalize(file_path, self.project_root)
        base_decision = self._evaluate_cached(norm_path)

        if base_decision.classification == FileClassification.CRITICAL:
            return base_decision

        if base_decision.classification == FileClassification.SENSITIVE and user_approved:
            return ProtectionDecision(
                path=norm_path,
                classification=base_decision.classification,
                status=DecisionStatus.APPROVED,
                rule_name=f"{base_decision.rule_name} (User Approved)",
                reason=f"User approved modification: {base_decision.reason}",
                risk_score=base_decision.risk_score,
                allow_review=True,
                allow_plan=True,
                allow_preview=True,
                allow_apply=True,
                requires_confirmation_phrase=False,
            )

        return base_decision

    @lru_cache(maxsize=512)
    def _evaluate_cached(self, norm_path: str) -> ProtectionDecision:
        for rule in self._rules:
            if rule.matches(norm_path):
                if rule.classification == FileClassification.CRITICAL:
                    return ProtectionDecision(
                        path=norm_path,
                        classification=FileClassification.CRITICAL,
                        status=DecisionStatus.BLOCKED,
                        rule_name=rule.name,
                        reason=f"CRITICAL: {rule.reason}",
                        risk_score=rule.risk_score,
                        allow_review=True,
                        allow_plan=True,
                        allow_preview=True,
                        allow_apply=False,
                        requires_confirmation_phrase=True,
                    )

                if rule.classification == FileClassification.SENSITIVE:
                    return ProtectionDecision(
                        path=norm_path,
                        classification=FileClassification.SENSITIVE,
                        status=DecisionStatus.PENDING_APPROVAL,
                        rule_name=rule.name,
                        reason=rule.reason,
                        risk_score=rule.risk_score,
                        allow_review=True,
                        allow_plan=True,
                        allow_preview=True,
                        allow_apply=False,
                        requires_confirmation_phrase=False,
                    )

                if rule.classification == FileClassification.NORMAL:
                    return ProtectionDecision(
                        path=norm_path,
                        classification=FileClassification.NORMAL,
                        status=DecisionStatus.APPROVED,
                        rule_name=rule.name,
                        reason=rule.reason,
                        risk_score=rule.risk_score,
                        allow_review=True,
                        allow_plan=True,
                        allow_preview=True,
                        allow_apply=True,
                        requires_confirmation_phrase=False,
                    )

        return ProtectionDecision(
            path=norm_path,
            classification=FileClassification.NORMAL,
            status=DecisionStatus.APPROVED,
            rule_name="default_normal",
            reason="Standard application file.",
            risk_score=15,
            allow_review=True,
            allow_plan=True,
            allow_preview=True,
            allow_apply=True,
            requires_confirmation_phrase=False,
        )


__all__ = [
    "FileClassification",
    "DecisionStatus",
    "ProtectionDecision",
    "ProtectionRule",
    "PathNormalizer",
    "ProtectionPolicy",
]