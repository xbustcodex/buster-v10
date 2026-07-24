"""
Action Router for Buster Kernel v10.5
Routes incoming system actions and agent requests to target handlers via EventBus & ServiceRegistry.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("buster.kernel.action_router")


class ActionRouter:
    """Central router for processing and dispatching system actions."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry
        self._action_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_action(self, action_type: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a specific action handler."""
        if action_type in self._action_handlers:
            logger.warning(f"Overwriting existing handler for action: '{action_type}'")
        self._action_handlers[action_type] = handler
        logger.info(f"Registered action handler: '{action_type}'")

    def unregister_action(self, action_type: str) -> bool:
        """Remove an action handler."""
        if action_type in self._action_handlers:
            del self._action_handlers[action_type]
            return True
        return False

    def dispatch(self, action_type: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Synchronously route and execute an action."""
        payload = payload or {}
        logger.debug(f"Dispatching action: '{action_type}'")

        if self.event_bus:
            self.event_bus.publish("action:dispatching", {"action": action_type, "payload": payload})

        handler = self._action_handlers.get(action_type)
        if not handler:
            err_msg = f"No registered handler for action type: '{action_type}'"
            logger.error(err_msg)
            if self.event_bus:
                self.event_bus.publish("action:error", {"action": action_type, "error": err_msg})
            raise KeyError(err_msg)

        try:
            result = handler(payload)
            if self.event_bus:
                self.event_bus.publish("action:success", {"action": action_type, "result": result})
            return result
        except Exception as exc:
            logger.exception(f"Error executing action '{action_type}': {exc}")
            if self.event_bus:
                self.event_bus.publish("action:failed", {"action": action_type, "error": str(exc)})
            raise

    def list_actions(self) -> Dict[str, str]:
        """List all active action routes."""
        return {action: handler.__name__ for action, handler in self._action_handlers.items()}