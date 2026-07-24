"""
Unified Automation Router for Buster Kernel v10.6
Master API binding Playwright, Desktop Automation, Vision Fallback, and Action Validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from buster.automation.action_validator import ActionValidator
from buster.automation.browser_automation import PlaywrightEngine
from buster.automation.desktop_automation import DesktopAutomationEngine
from buster.automation.vision_fallback import VisionFallbackHandler

logger = logging.getLogger("buster.automation.router")


class UnifiedAutomationRouter:
    """Master controller routing web, desktop, and visual actions."""

    def __init__(self, event_bus=None, security_intercept=None):
        self.event_bus = event_bus
        self.security = security_intercept

        self.browser = PlaywrightEngine(event_bus=event_bus, security_intercept=security_intercept)
        self.desktop = DesktopAutomationEngine(event_bus=event_bus, security_intercept=security_intercept)
        self.vision = VisionFallbackHandler(event_bus=event_bus, security_intercept=security_intercept)
        self.validator = ActionValidator(event_bus=event_bus)

    async def execute_web_action(self, action_type: str, target: str, value: str = "") -> bool:
        """Routes web browser interactions."""
        logger.info(f"Executing web action '{action_type}' on '{target}'")
        if action_type == "navigate":
            return await self.browser.navigate(target)
        elif action_type == "click":
            return await self.browser.click(target)
        elif action_type == "fill":
            return await self.browser.fill_text(target, value)
        else:
            logger.error(f"Unknown web action type: {action_type}")
            return False

    def execute_desktop_action(self, action_type: str, **kwargs) -> bool:
        """Routes native desktop interactions."""
        logger.info(f"Executing desktop action '{action_type}' with args {kwargs}")
        if action_type == "focus":
            return self.desktop.focus_window(kwargs.get("title", ""))
        elif action_type == "click":
            return self.desktop.click_coordinate(kwargs.get("x", 0), kwargs.get("y", 0))
        elif action_type == "type":
            return self.desktop.type_text(kwargs.get("text", ""))
        elif action_type == "hotkey":
            return self.desktop.press_hotkey(*kwargs.get("keys", []))
        else:
            logger.error(f"Unknown desktop action type: {action_type}")
            return False

    def resolve_visual_click(self, screenshot_path: str, template_path: str) -> bool:
        """Fallback routine: locates visual target and executes desktop click."""
        coords = self.vision.locate_visual_target(screenshot_path, template_path)
        if coords:
            return self.desktop.click_coordinate(coords[0], coords[1])
        return False