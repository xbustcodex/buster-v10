from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from buster.rhythm.rhythm import LifeState

logger = logging.getLogger(__name__)


@dataclass
class SleepResponse:
    interrupted: bool
    mode: str  # "GROGGY", "DND", or "AWAKE"
    message: str
    allow_execution: bool


class SleepInterruptionHandler:
    """Handles incoming prompts and tasks during Buster's sleep cycle."""

    def __init__(self, dnd_enabled: bool = False, urgent_keywords: Optional[list[str]] = None) -> None:
        self.dnd_enabled = dnd_enabled
        self.urgent_keywords = urgent_keywords or ["urgent", "emergency", "wake up", "override", "critical"]

    def process_prompt_during_sleep(
        self,
        prompt: str,
        current_state: LifeState | str = LifeState.SLEEP,
    ) -> SleepResponse:
        state_str = str(current_state.value if isinstance(current_state, LifeState) else current_state).upper()

        if "SLEEP" not in state_str:
            return SleepResponse(
                interrupted=False,
                mode="AWAKE",
                message="",
                allow_execution=True,
            )

        is_urgent = any(kw in prompt.lower() for kw in self.urgent_keywords)

        if self.dnd_enabled and not is_urgent:
            logger.info("Sleep prompt blocked by DND mode.")
            return SleepResponse(
                interrupted=False,
                mode="DND",
                message="[DND Active] Buster is currently in deep sleep cycle. Wake keyword required to interrupt.",
                allow_execution=False,
            )

        if is_urgent:
            logger.info("Sleep interrupted by urgent override keyword.")
            return SleepResponse(
                interrupted=True,
                mode="AWAKE",
                message="*rubs eyes* Emergency override detected. Systems fully online.",
                allow_execution=True,
            )

        # Default: Groggy response mode
        logger.info("Sleep prompt processed under Groggy Mode.")
        return SleepResponse(
            interrupted=True,
            mode="GROGGY",
            message="*yawn* Hmm? I'm currently in sleep cycle... processing this on low battery mode.",
            allow_execution=True,
        )