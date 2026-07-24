"""
Buster Kernel - System Audit & Operational History Engine

Provides a tamper-evident, hash-chained JSONL audit ledger for tracking
all autonomous agent actions, permission checks, and state mutations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BusterKernel.AuditService")

GENESIS_HASH = "GENESIS_HASH_00000000000000000000000000000000"


@dataclass
class AuditRecord:
    """Tamper-evident audit entry envelope with causal execution tracing."""
    record_id: str = field(
        default_factory=lambda: f"AUD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:17]}"
    )
    transaction_id: str = "T-000000"  # Global top-level execution run ID
    task_id: str = "TASK-000"          # Specific task assignment
    action_id: str = "ACT-00"          # Granular step index within task
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    agent_id: str = "system"
    action: str = "UNKNOWN_ACTION"
    target: str = "N/A"
    permission_status: str = "UNKNOWN"   # GRANTED | DENIED | BYPASS
    execution_result: str = "PENDING"    # SUCCESS | FAILED | ABORTED
    verification_status: str = "UNVERIFIED"  # PASSED | FAILED | SKIPPED
    previous_hash: str = GENESIS_HASH
    record_hash: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class AuditService:
    """
    Tamper-evident, hash-chained kernel audit ledger with canonical serialization,
    thread-safe concurrent appends, recovery validation, and truncation protection.
    """

    def __init__(self, log_dir: str = "logs/audit", checkpoint_dir: str = "data") -> None:
        self.log_path = Path(log_dir)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_path = Path(checkpoint_dir)
        self.checkpoint_path.mkdir(parents=True, exist_ok=True)
        self._checkpoint_file = self.checkpoint_path / "audit_checkpoint.json"

        self._current_session_file = (
            self.log_path / f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        )
        self._records: List[AuditRecord] = []
        self._write_lock = threading.RLock()

        # Recovery validation on boot
        self._last_hash: str = self._recover_and_validate_chain()
        logger.info(f"Audit Service initialized. Chain tip: {self._last_hash[:12]}...")

    @staticmethod
    def _canonical_json(data: dict) -> str:
        """Produces deterministic, canonical JSON for stable cryptographic hashing."""
        return json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        )

    def _compute_hash(self, record_dict: dict, prev_hash: str) -> str:
        """Computes SHA-256 over record payload excluding `record_hash`."""
        payload = record_dict.copy()
        payload.pop("record_hash", None)
        payload["previous_hash"] = prev_hash

        canonical_payload = self._canonical_json(payload)
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    def _update_checkpoint(self, last_hash: str) -> None:
        """Writes out-of-band chain tip checkpoint to detect historical truncation."""
        try:
            checkpoint_data = {
                "last_hash": last_hash,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "file": str(self._current_session_file)
            }
            with open(self._checkpoint_file, "w", encoding="utf-8") as f:
                f.write(self._canonical_json(checkpoint_data))
        except Exception as err:
            logger.error(f"Failed to update out-of-band audit checkpoint: {err}")

    def _recover_and_validate_chain(self) -> str:
        """Validates ledger from line 1 on startup before resuming chain updates."""
        if not self._current_session_file.exists():
            return GENESIS_HASH

        expected_prev_hash = GENESIS_HASH
        last_valid_hash = GENESIS_HASH

        try:
            with open(self._current_session_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    entry = json.loads(line)
                    if entry.get("previous_hash") != expected_prev_hash:
                        logger.critical(f"Audit Boot Recovery Failed: Hash break on line {line_num}")
                        return GENESIS_HASH

                    computed = self._compute_hash(entry, expected_prev_hash)
                    if entry.get("record_hash") != computed:
                        logger.critical(f"Audit Boot Recovery Failed: Corrupted record on line {line_num}")
                        return GENESIS_HASH

                    expected_prev_hash = entry.get("record_hash")
                    last_valid_hash = expected_prev_hash

            # Verify against out-of-band checkpoint for end-of-file truncation
            if self._checkpoint_file.exists():
                try:
                    with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                        checkpoint = json.loads(f.read())
                        saved_tip = checkpoint.get("last_hash")
                        if checkpoint.get("file") == str(self._current_session_file) and saved_tip != last_valid_hash:
                            logger.critical(
                                f"TRUNCATION DETECTED! Checkpoint tip ({saved_tip[:12]}...) "
                                f"does not match log tip ({last_valid_hash[:12]}...)"
                            )
                except Exception as err:
                    logger.warning(f"Could not read audit checkpoint file: {err}")

            return last_valid_hash

        except Exception as err:
            logger.error(f"Error recovering audit ledger: {err}")
            return GENESIS_HASH

    def log_action(
        self,
        agent_id: str,
        action: str,
        target: str,
        permission_status: str = "GRANTED",
        execution_result: str = "SUCCESS",
        verification_status: str = "PASSED",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Thread-safe append of a hash-chained record to the audit ledger."""
        with self._write_lock:
            record = AuditRecord(
                agent_id=agent_id,
                action=action,
                target=target,
                permission_status=permission_status,
                execution_result=execution_result,
                verification_status=verification_status,
                previous_hash=self._last_hash,
                details=details or {},
            )

            record_dict = asdict(record)
            record.record_hash = self._compute_hash(record_dict, self._last_hash)
            
            # Advance chain tip and checkpoint
            self._last_hash = record.record_hash
            self._update_checkpoint(self._last_hash)

            self._records.append(record)
            self._persist_record(record)
            return record

    def _persist_record(self, record: AuditRecord) -> None:
        """Appends record using canonical JSON serialization."""
        try:
            with open(self._current_session_file, "a", encoding="utf-8") as f:
                f.write(self._canonical_json(asdict(record)) + "\n")
        except Exception as err:
            logger.error(f"Failed to append to audit ledger: {err}")

    def query_by_agent(self, agent_id: str) -> List[AuditRecord]:
        """Filters recorded actions by worker agent."""
        with self._write_lock:
            return [r for r in self._records if r.agent_id == agent_id]

    def log_event(self, event: Any) -> None:
        """EventRouter hook: automatically parses KernelEvents into AuditRecords."""
        topic = getattr(event, "topic", "raw_event")
        source = getattr(event, "source", "unknown")
        payload = getattr(event, "payload", {})

        self.log_action(
            agent_id=source,
            action=topic,
            target=payload.get("target", "kernel"),
            permission_status=payload.get("permission", "GRANTED"),
            execution_result=payload.get("status", "SUCCESS"),
            verification_status=payload.get("verification", "PASSED"),
            details=payload,
        )

    def verify_integrity(self) -> bool:
        """Validates ledger for content alterations, chain breaks, and truncation."""
        with self._write_lock:
            if not self._current_session_file.exists():
                return True

            expected_prev_hash = GENESIS_HASH
            last_valid_hash = GENESIS_HASH

            try:
                with open(self._current_session_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, start=1):
                        line = line.strip()
                        if not line:
                            continue

                        entry = json.loads(line)

                        if entry.get("previous_hash") != expected_prev_hash:
                            logger.error(f"Integrity Error (Line {line_num}): Chain break.")
                            return False

                        recomputed = self._compute_hash(entry, expected_prev_hash)
                        if entry.get("record_hash") != recomputed:
                            logger.error(f"Integrity Error (Line {line_num}): Content tamper detected.")
                            return False

                        expected_prev_hash = entry.get("record_hash")
                        last_valid_hash = expected_prev_hash

                # Out-of-band truncation verification
                if self._checkpoint_file.exists():
                    with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                        checkpoint = json.loads(f.read())
                        if checkpoint.get("file") == str(self._current_session_file):
                            if checkpoint.get("last_hash") != last_valid_hash:
                                logger.error("Integrity Error: File truncation detected via out-of-band checkpoint.")
                                return False

                logger.info("Audit ledger integrity successfully verified.")
                return True

            except Exception as err:
                logger.error(f"Audit verification error: {err}")
                return False