# buster/capabilities/health.py
from __future__ import annotations

import datetime
import logging
from typing import Dict, Any

from buster.capabilities.models import CapabilityHealth

logger = logging.getLogger(__name__)


class HealthEvaluator:
    """Helper for constructing standardized health records."""

    @staticmethod
    def create_health(
        capability_id: str,
        status: str,
        latency_ms: float | None = None,
        message: str = "",
        diagnostics: Dict[str, Any] | None = None,
    ) -> CapabilityHealth:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        return CapabilityHealth(
            capability_id=capability_id,
            status=status,
            checked_at=now,
            latency_ms=latency_ms,
            message=message,
            diagnostics=diagnostics or {},
        )