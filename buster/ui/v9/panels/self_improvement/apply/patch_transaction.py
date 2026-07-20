"""
Buster Patch Transaction Manager v5.0

Enforces an atomic transaction lifecycle with continuous lifecycle audit logging,
preflight safety gates, agent causal linking, event sequencing, and schema versioning.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import py_compile
import shutil
import subprocess
import time
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from buster.runtime.audit_service import AuditService
from buster.ui.v9.panels.self_improvement.apply.preflight import PreflightChecker

logger = logging.getLogger("buster.patch_transaction")


class TransactionState(Enum):
    PENDING = auto()
    PREFLIGHT_PASSED = auto()
    IN_PROGRESS = auto()
    BACKUP_COMPLETE = auto()
    APPLIED = auto()
    COMPILED = auto()
    VERIFIED = auto()
    TESTED = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()
    FAILED = auto()


class PatchTransaction:
    """Full-lifecycle deployment transaction with complete causal telemetry and schema versioning."""

    EVENT_SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        patch_id: str,
        transaction_id: str,
        project_root: Union[str, Path],
        target_rel_path: str,
        new_content: str,
        audit_service: AuditService,
        agent_id: str = "BuilderAgent",
        parent_patch_id: Optional[str] = None,
        executor: str = "AI",
        runtime_version: str = "10.2.0",
        event_emitter: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self.patch_id = patch_id
        self.transaction_id = transaction_id
        self.project_root = Path(project_root).resolve()
        self.target_file = (self.project_root / target_rel_path).resolve()
        self.target_rel_path = target_rel_path
        self.new_content = new_content
        self.audit_service = audit_service
        self.agent_id = agent_id
        self.parent_patch_id = parent_patch_id
        self.executor = executor
        self.runtime_version = runtime_version
        self.host_id = platform.node() or "unknown_host"
        self.event_emitter = event_emitter

        self.state = TransactionState.PENDING
        self.backup_path: Optional[Path] = None
        self.error_message: Optional[str] = None
        self.git_commit_hash: Optional[str] = None
        
        # Telemetry & Sequencing
        self._sequence: int = 0
        self._stage_start_time: float = time.perf_counter()

    def _log_event(self, stage: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Records granular lifecycle events with complete telemetry, monotonic sequence numbers, and schema version."""
        now = time.perf_counter()
        duration_ms = round((now - self._stage_start_time) * 1000, 2)
        self._stage_start_time = now  # Reset timer for the next stage
        self._sequence += 1

        payload = {
            "event_schema": self.EVENT_SCHEMA_VERSION,
            "patch_id": self.patch_id,
            "parent_patch_id": self.parent_patch_id,
            "transaction_id": self.transaction_id,
            "sequence": self._sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "duration_ms": duration_ms,
            "agent_id": self.agent_id,
            "executor": self.executor,
            "runtime_version": self.runtime_version,
            "host_id": self.host_id,
            "target": self.target_rel_path,
            "state": self.state.name,
        }
        if details:
            payload.update(details)

        # 1. Continuous Audit Record Logging
        self.audit_service.record(payload)

        # 2. Central Runtime Event Broadcast
        if self.event_emitter:
            try:
                self.event_emitter(stage, payload)
            except Exception as err:
                logger.error("[%s] Event broadcast error: %s", self.patch_id, err)

    def run_preflight(self) -> bool:
        """Runs preflight verification checks before BEGIN."""
        self._stage_start_time = time.perf_counter()
        checker = PreflightChecker(self.project_root)
        passed, failures = checker.run_all(self.target_rel_path)

        if not passed:
            self.state = TransactionState.FAILED
            self._log_event("PREFLIGHT_FAILED", {"reasons": failures})
            return False

        self.state = TransactionState.PREFLIGHT_PASSED
        self._log_event("PREFLIGHT_PASSED")
        return True

    def begin(self) -> bool:
        """Stage 1: Preflight checks & timestamped backup creation."""
        if not self.run_preflight():
            return False

        self.state = TransactionState.IN_PROGRESS
        self._log_event("TRANSACTION_BEGIN")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / "Backups" / f"{timestamp}_{self.patch_id}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if self.target_file.exists():
            self.backup_path = backup_dir / self.target_file.name
            shutil.copy2(self.target_file, self.backup_path)

            manifest = {
                "event_schema": self.EVENT_SCHEMA_VERSION,
                "patch_id": self.patch_id,
                "parent_patch_id": self.parent_patch_id,
                "transaction_id": self.transaction_id,
                "agent_id": self.agent_id,
                "target": str(self.target_rel_path),
                "backup": str(self.backup_path),
                "timestamp": timestamp,
            }
            with open(backup_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

        self.state = TransactionState.BACKUP_COMPLETE
        self._log_event("BACKUP_COMPLETE", {"backup_path": str(self.backup_path)})
        return True

    def apply_and_compile(self) -> bool:
        """Stage 2: Write patch to target file and compile bytecode."""
        if self.state != TransactionState.BACKUP_COMPLETE:
            raise RuntimeError(f"[{self.patch_id}] Cannot apply without backup.")

        try:
            with open(self.target_file, "w", encoding="utf-8") as f:
                f.write(self.new_content)

            self.state = TransactionState.APPLIED
            self._log_event("APPLY_COMPLETE")

            py_compile.compile(str(self.target_file), doraise=True)
            self.state = TransactionState.COMPILED
            self._log_event("COMPILE_PASSED")
            return True
        except Exception as exc:
            self.error_message = f"Compile failed: {exc}"
            self._log_event("COMPILE_FAILED", {"error": str(exc)})
            self.rollback(reason="Compilation Failure")
            return False

    def run_verification(self, verifier_func: Optional[Callable[[], Tuple[bool, str]]] = None) -> bool:
        """Stage 3: Static analysis and invariant checks."""
        if self.state != TransactionState.COMPILED:
            raise RuntimeError(f"[{self.patch_id}] Cannot verify prior to compile.")

        if verifier_func:
            passed, reason = verifier_func()
            if not passed:
                self.error_message = f"Verification failed: {reason}"
                self._log_event("VERIFICATION_FAILED", {"reason": reason})
                self.rollback(reason="Verification Failure")
                return False

        self.state = TransactionState.VERIFIED
        self._log_event("VERIFICATION_PASSED")
        return True

    def run_tests(self, test_cmd: Optional[List[str]] = None) -> bool:
        """Stage 4: Unit/Integration test suite check."""
        if self.state != TransactionState.VERIFIED:
            raise RuntimeError(f"[{self.patch_id}] Cannot test prior to verification.")

        if test_cmd:
            try:
                res = subprocess.run(
                    test_cmd,
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if res.returncode != 0:
                    err_msg = res.stderr or res.stdout
                    self.error_message = f"Tests failed: {err_msg}"
                    self._log_event("TESTS_FAILED", {"output": err_msg})
                    self.rollback(reason="Test Suite Failure")
                    return False
            except Exception as exc:
                self.error_message = f"Test execution error: {exc}"
                self._log_event("TESTS_FAILED", {"error": str(exc)})
                self.rollback(reason="Test Execution Error")
                return False

        self.state = TransactionState.TESTED
        self._log_event("TESTS_PASSED")
        return True

    def commit_git(self) -> bool:
        """Stage 5: Commit to local git repository."""
        try:
            subprocess.run(
                ["git", "add", str(self.target_rel_path)],
                cwd=str(self.project_root),
                check=True,
                capture_output=True,
            )
            msg = f"auto({self.agent_id}): Apply {self.patch_id} (Tx: {self.transaction_id}) to {self.target_rel_path}"
            res = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                hash_res = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                )
                self.git_commit_hash = hash_res.stdout.strip()[:8]
                self._log_event("GIT_COMMIT_COMPLETE", {"commit": self.git_commit_hash})
        except Exception as err:
            logger.warning("[%s] Git commit step skipped: %s", self.patch_id, err)

        return True

    def commit(self) -> None:
        """Stage 6: Mark committed and final audit entry."""
        self.commit_git()
        self.state = TransactionState.COMMITTED
        self._log_event("TRANSACTION_COMMITTED", {"commit_hash": self.git_commit_hash})

    def rollback(self, reason: str = "Unspecified Failure") -> None:
        """Restores file state from backup and audits rollback lifecycle events."""
        self._log_event("ROLLBACK_STARTED", {"reason": reason, "error": self.error_message})

        if self.backup_path and self.backup_path.exists():
            shutil.copy2(self.backup_path, self.target_file)
            self._log_event("ROLLBACK_COMPLETE", {"restored_from": str(self.backup_path)})

        self.state = TransactionState.ROLLED_BACK
        self._log_event("TRANSACTION_ROLLED_BACK", {"reason": reason})