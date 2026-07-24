"""
Playwright Web Automation Engine for Buster Kernel v10.6
Provides headless/headed browser control, page interaction, screenshotting, and DOM scraping.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger("buster.automation.browser")


class PlaywrightEngine:
    """Async web automation runner using Playwright."""

    def __init__(self, event_bus=None, security_intercept=None):
        self.event_bus = event_bus
        self.security = security_intercept
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None

    async def initialize(self, headless: bool = True) -> None:
        """Starts Playwright and launches the primary browser instance."""
        if self._browser:
            return

        logger.info("Initializing Playwright Engine...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context()
        self._active_page = await self._context.new_page()

        if self.event_bus:
            self.event_bus.publish("browser:initialized", {"headless": headless})

    async def navigate(self, url: str) -> bool:
        """Navigates the active page to the target URL."""
        if not self._active_page:
            await self.initialize()

        logger.info(f"Navigating to '{url}'...")
        try:
            response = await self._active_page.goto(url, wait_until="networkidle")
            status = response.status if response else 0
            
            if self.event_bus:
                self.event_bus.publish("browser:navigated", {"url": url, "status": status})
            return status < 400
        except Exception as exc:
            logger.error(f"Navigation to '{url}' failed: {exc}")
            if self.event_bus:
                self.event_bus.publish("browser:error", {"action": "navigate", "error": str(exc)})
            return False

    async def click(self, selector: str) -> bool:
        """Clicks an element identified by CSS selector or text."""
        if not self._active_page:
            return False

        try:
            await self._active_page.click(selector, timeout=5000)
            if self.event_bus:
                self.event_bus.publish("browser:clicked", {"selector": selector})
            return True
        except Exception as exc:
            logger.error(f"Failed to click selector '{selector}': {exc}")
            return False

    async def fill_text(self, selector: str, text: str) -> bool:
        """Fills an input or textarea with specified text."""
        if not self._active_page:
            return False

        try:
            await self._active_page.fill(selector, text, timeout=5000)
            if self.event_bus:
                self.event_bus.publish("browser:filled", {"selector": selector})
            return True
        except Exception as exc:
            logger.error(f"Failed to fill text into '{selector}': {exc}")
            return False

    async def capture_screenshot(self, output_path: str | Path) -> Tuple[bool, str]:
        """Captures a screenshot of the active viewport."""
        if not self._active_page:
            return False, "Browser page not initialized"

        path_obj = Path(output_path).resolve()
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            await self._active_page.screenshot(path=str(path_obj), full_page=False)
            if self.event_bus:
                self.event_bus.publish("browser:screenshot", {"path": str(path_obj)})
            return True, str(path_obj)
        except Exception as exc:
            logger.error(f"Failed to capture screenshot: {exc}")
            return False, str(exc)

    async def close(self) -> None:
        """Shuts down Playwright and closes all open contexts."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright Engine closed.")