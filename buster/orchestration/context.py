# buster/orchestration/context.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional


class MissionContext:
    """Manages state, intermediate task outputs, and variable interpolation during mission execution."""

    def __init__(self, mission_id: str, initial_variables: Optional[Dict[str, Any]] = None) -> None:
        self.mission_id = mission_id
        self.variables: Dict[str, Any] = initial_variables or {}
        self.outputs: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}

    def set_output(self, task_id: str, result: Any) -> None:
        self.outputs[task_id] = result

    def set_error(self, task_id: str, error_msg: str) -> None:
        self.errors[task_id] = error_msg

    def resolve_value(self, value: Any) -> Any:
        """Recursively resolves template strings like {outputs.task_id.key} or {variables.var_name}."""
        if isinstance(value, str):
            # Check for exact match or string interpolation
            pattern = re.compile(r"\{([a-zA-Z0-9_\.]+)\}")
            
            # If the entire string is just a single placeholder, return the exact object type
            match = pattern.fullmatch(value)
            if match:
                path = match.group(1)
                return self._lookup_path(path)

            # Otherwise, perform string substitution
            def replace_match(m: re.Match) -> str:
                res = self._lookup_path(m.group(1))
                return str(res) if res is not None else m.group(0)

            return pattern.sub(replace_match, value)

        elif isinstance(value, dict):
            return {k: self.resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_value(item) for item in value]
        
        return value

    def _lookup_path(self, path: str) -> Any:
        parts = path.split(".")
        current: Any = self.__dict__
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current