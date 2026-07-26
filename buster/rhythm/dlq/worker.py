from __future__ import annotations

import logging
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DLQRecoveryWorker:
    """Processes ready items from the RhythmDLQManager during appropriate rhythm states."""

    def __init__(self, dlq_manager: Any, execution_engine: Optional[Any] = None) -> None:
        self.dlq_manager = dlq_manager
        self.execution_engine = execution_engine

    def process_ready_items(self, now: Optional[datetime] = None) -> int:
        """Fetches ready DLQ items and attempts to re-execute or re-enqueue them."""
        ready_items = self.dlq_manager.get_ready_items(now=now)
        processed_count = 0

        for item in ready_items:
            logger.info(f"Processing DLQ recovery item {item.item_id} (Task: {item.task_name}, Strategy: {item.recovery_strategy})")
            try:
                success = False
                if self.execution_engine and hasattr(self.execution_engine, "execute_task"):
                    result = self.execution_engine.execute_task(item.task_name, item.payload)
                    success = getattr(result, "success", True)
                else:
                    success = True

                if success:
                    self.dlq_manager.mark_resolved(item.item_id)
                    logger.info(f"Successfully recovered DLQ item {item.item_id}")
                else:
                    self.dlq_manager.mark_failed(item.item_id, "Execution returned failure status during recovery")
                    logger.warning(f"Recovery failed for DLQ item {item.item_id}")

                processed_count += 1
            except Exception as e:
                logger.exception(f"Error recovering DLQ item {item.item_id}: {e}")
                self.dlq_manager.mark_failed(item.item_id, str(e))
                processed_count += 1

        return processed_count