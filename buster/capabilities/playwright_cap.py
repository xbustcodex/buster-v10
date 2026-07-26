# buster/capabilities/playwright_cap.py
from __future__ import annotations

import time
from typing import Any, Mapping

from buster.capabilities.base import Capability
from buster.capabilities.models import (
    CapabilityDescriptor,
    CapabilityHealth,
    CapabilityExecutionContext,
    CapabilityResult,
    ActionDescriptor,
    ResourceRequirements,
)
from buster.capabilities.permissions import PermissionGate
from buster.capabilities.health import HealthEvaluator
from buster.capabilities.exceptions import ActionNotSupportedError, ActionValidationError, CapabilityDisabledError


class PlaywrightCapability(Capability):
    capability_id = "core.playwright"
    name = "Playwright Browser Automation Capability"
    version = "1.0.0"

    def __init__(self, registry_ref=None) -> None:
        self._registry_ref = registry_ref

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            capability_id=self.capability_id,
            name=self.name,
            version=self.version,
            description="Provides web page navigation, scraping, and browser automation.",
            actions=(
                ActionDescriptor(
                    name="playwright.fetch_page",
                    description="Navigates to a URL and returns page title and text content.",
                    input_schema={"url": "str"},
                    output_schema={"title": "str", "text_content": "str"},
                    required_permissions=("network.access",),
                    risk_level="medium",
                ),
            ),
            required_permissions=("network.access",),
            resource_requirements=ResourceRequirements(cpu_cores=1.0, memory_mb=512, requires_network=True),
            provider="buster",
            tags=("browser", "playwright", "web"),
            enabled_by_default=True,
        )

    def health_check(self) -> CapabilityHealth:
        start = time.perf_counter()
        try:
            import playwright
            latency = (time.perf_counter() - start) * 1000.0
            return HealthEvaluator.create_health(
                self.capability_id,
                "HEALTHY",
                latency_ms=latency,
                message="Playwright package installed.",
                diagnostics={"package_found": True},
            )
        except ImportError:
            return HealthEvaluator.create_health(self.capability_id, "DEGRADED", message="Playwright package not installed.")

    def execute(
        self,
        action: str,
        arguments: Mapping[str, Any],
        context: CapabilityExecutionContext,
    ) -> CapabilityResult:
        start_time = time.perf_counter()
        desc = self.describe()

        if self._registry_ref and not self._registry_ref.is_enabled(self.capability_id):
            raise CapabilityDisabledError(f"Capability '{self.capability_id}' is disabled.")

        action_desc = next((a for a in desc.actions if a.name == action), None)
        if not action_desc:
            raise ActionNotSupportedError(f"Action '{action}' not supported.")

        PermissionGate.verify_permissions(desc, action_desc, context)

        url = arguments.get("url")
        if not url:
            raise ActionValidationError("Argument 'url' is required.")

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url)
                title = page.title()
                text_content = page.inner_text("body")
                browser.close()

            output = {"title": title, "text_content": text_content[:5000]}
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=True, capability_id=self.capability_id, action=action, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return CapabilityResult(success=False, capability_id=self.capability_id, action=action, error=str(e), duration_ms=duration)