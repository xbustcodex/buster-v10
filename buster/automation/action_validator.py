from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from PIL import Image, ImageChops

logger = logging.getLogger("buster.automation.validator")


class ActionValidator:
    """Verifies automation outcomes by analyzing state and visual changes."""

    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def compare_screenshots(
        self, before_path: str | Path, after_path: str | Path, threshold: float = 0.01
    ) -> Tuple[bool, float]:
        """
        Compares two screenshots to verify if a visual change occurred.
        Returns (has_changed, change_percentage).
        """
        p_before = Path(before_path).resolve()
        p_after = Path(after_path).resolve()

        if not p_before.exists() or not p_after.exists():
            logger.error("Before or After screenshot path does not exist.")
            return False, 0.0

        try:
            img1 = Image.open(p_before).convert("RGB")
            img2 = Image.open(p_after).convert("RGB")

            # Resize if dimensions differ slightly
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)

            diff = ImageChops.difference(img1, img2)

            # Calculate mean difference across pixels
            stat = diff.getbbox()
            if stat is None:
                # Images are 100% identical
                return False, 0.0

            # Calculate basic pixel variance ratio
            histogram = diff.histogram()
            non_zero_pixels = sum(histogram[1:])
            total_pixels = img1.size[0] * img1.size[1] * 3
            change_ratio = round(non_zero_pixels / float(total_pixels), 4)

            has_changed = change_ratio >= threshold

            if self.event_bus:
                self.event_bus.publish(
                    "validator:diff_calculated",
                    {"has_changed": has_changed, "change_ratio": change_ratio},
                )

            return has_changed, change_ratio

        except Exception as exc:
            logger.error(f"Action validation comparison failed: {exc}")
            return False, 0.0

    def validate_action_result(
        self, before_state: Dict[str, Any], after_state: Dict[str, Any]
    ) -> bool:
        """Validates key structural changes between before and after dictionary states."""
        diff_keys = [
            k for k in after_state if after_state.get(k) != before_state.get(k)
        ]
        is_valid = len(diff_keys) > 0

        logger.info(
            f"Action state validation result: {is_valid} (Changed keys: {diff_keys})"
        )
        return is_valid

    def execute_with_verification(
        self,
        perception_fn: Callable[[], Dict[str, Any]],
        action_fn: Callable[[], Any],
        settle_time_seconds: float = 0.1,
    ) -> Dict[str, Any]:
        """PAV Loop execution wrapper."""
        try:
            pre_state = perception_fn() or {}
            action_fn()

            if settle_time_seconds > 0:
                time.sleep(settle_time_seconds)

            post_state = perception_fn() or {}
            has_changed = self.validate_action_result(pre_state, post_state)

            return {
                "success": True,
                "delta_detected": has_changed,
                "pre_state": pre_state,
                "post_state": post_state,
            }
        except Exception as exc:
            logger.error(f"PAV Loop execution failed: {exc}")
            return {
                "success": False,
                "delta_detected": False,
                "pre_state": {},
                "post_state": {},
                "error": str(exc),
            }