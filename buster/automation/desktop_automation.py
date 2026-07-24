"""
Windows GUI Automation Engine for Buster Kernel v10.6
Provides native window management, keyboard/mouse input simulation, and active app tracking.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import pyautogui
import pygetwindow as gw

logger = logging.getLogger("buster.automation.desktop")

# Safety fail-safe: moving mouse to corner stops execution
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


class DesktopAutomationEngine:
    """Native OS window control and input simulation module."""

    def __init__(self, event_bus=None, security_intercept=None):
        self.event_bus = event_bus
        self.security = security_intercept

    def list_open_windows(self) -> List[str]:
        """Returns titles of all active desktop windows."""
        windows = gw.getAllTitles()
        active = [title.strip() for title in windows if title.strip()]
        return active

    def focus_window(self, title_query: str) -> bool:
        """Finds and brings a target window to the foreground."""
        matches = gw.getWindowsWithTitle(title_query)
        if not matches:
            logger.warning(f"No window found matching title '{title_query}'")
            return False

        try:
            win = matches[0]
            if win.isMinimized:
                win.restore()
            win.activate()

            if self.event_bus:
                self.event_bus.publish("desktop:window_focused", {"title": win.title})
            return True
        except Exception as exc:
            logger.error(f"Failed to focus window '{title_query}': {exc}")
            return False

    def click_coordinate(self, x: int, y: int, clicks: int = 1, button: str = "left") -> bool:
        """Simulates mouse clicks at specific screen coordinates."""
        try:
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            if self.event_bus:
                self.event_bus.publish(
                    "desktop:clicked", {"x": x, "y": y, "clicks": clicks, "button": button}
                )
            return True
        except Exception as exc:
            logger.error(f"Click at ({x}, {y}) failed: {exc}")
            return False

    def type_text(self, text: str, interval: float = 0.02) -> bool:
        """Simulates keyboard input into the currently focused window."""
        try:
            pyautogui.write(text, interval=interval)
            if self.event_bus:
                self.event_bus.publish("desktop:typed", {"text_length": len(text)})
            return True
        except Exception as exc:
            logger.error(f"Type text failed: {exc}")
            return False

    def press_hotkey(self, *keys: str) -> bool:
        """Executes a key combination (e.g., 'ctrl', 'c' or 'alt', 'tab')."""
        try:
            pyautogui.hotkey(*keys)
            if self.event_bus:
                self.event_bus.publish("desktop:hotkey", {"keys": list(keys)})
            return True
        except Exception as exc:
            logger.error(f"Hotkey '{keys}' failed: {exc}")
            return False