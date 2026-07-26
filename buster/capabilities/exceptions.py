# buster/capabilities/exceptions.py
from __future__ import annotations


class CapabilityError(Exception):
    """Base exception for all capability errors."""


class CapabilityNotFoundError(CapabilityError):
    """Raised when a requested capability ID is not registered."""


class DuplicateCapabilityError(CapabilityError):
    """Raised when attempting to register a capability ID that already exists."""


class InvalidCapabilityDescriptorError(CapabilityError):
    """Raised when a capability descriptor fails validation."""


class ActionNotSupportedError(CapabilityError):
    """Raised when an action is requested that is not declared in the capability descriptor."""


class ActionValidationError(CapabilityError):
    """Raised when action arguments fail input schema validation."""


class PermissionDeniedError(CapabilityError):
    """Raised when execution is blocked by the permission gate."""


class CapabilityDisabledError(CapabilityError):
    """Raised when attempting to execute an action on a disabled capability."""