from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ServiceResolver:
    """Helper to safely discover runtime capabilities and services from runtime_core."""

    @staticmethod
    def get_service(runtime_core: Any) -> Any:
        if runtime_core is None:
            return None
        return getattr(runtime_core, "self_improvement", None) or getattr(
            runtime_core, "self_improvement_service", None
        ) or getattr(runtime_core, "autonomy_service", None)

    @staticmethod
    def get_status(runtime_core: Any) -> dict[str, Any]:
        if runtime_core is None:
            return {}

        def _normalize(val: Any) -> dict[str, Any] | None:
            if hasattr(val, "to_dict") and callable(val.to_dict):
                try:
                    val = val.to_dict()
                except Exception:
                    pass
            if isinstance(val, dict):
                return val
            if isinstance(val, list):
                return {"findings": val}
            return None

        # 1. Try runtime_core helper methods
        for attr_name in ("self_improvement_status", "get_self_improvement_status", "get_status"):
            helper = getattr(runtime_core, attr_name, None)
            if callable(helper):
                try:
                    res = _normalize(helper())
                    if res is not None:
                        return res
                except Exception as exc:
                    logger.debug(f"Failed calling {attr_name}: {exc}")

        # 2. Try self_improvement / autonomy services
        for service_attr in ("self_improvement", "self_improvement_service", "autonomy_service"):
            service = getattr(runtime_core, service_attr, None)
            if service is not None:
                for method_name in ("status", "get_status", "get_self_improvement_status"):
                    status_fn = getattr(service, method_name, None)
                    if callable(status_fn):
                        try:
                            res = _normalize(status_fn())
                            if res is not None:
                                return res
                        except Exception as exc:
                            logger.debug(f"Failed calling status on service: {exc}")

                # Check direct list attributes on the service
                for list_attr in ("findings", "active_findings", "results", "scan_results"):
                    val = getattr(service, list_attr, None)
                    if isinstance(val, list):
                        return {"findings": val}

        # 3. Direct attributes on runtime_core
        for list_attr in ("findings", "active_findings", "scan_results"):
            val = getattr(runtime_core, list_attr, None)
            if isinstance(val, list):
                return {"findings": val}

        return {}

    @staticmethod
    def resolve_diff_provider(runtime_core: Any) -> Any:
        candidates = (
            getattr(runtime_core, "diff_generator", None),
            getattr(runtime_core, "code_generator", None),
            getattr(runtime_core, "ai_manager", None),
            getattr(getattr(runtime_core, "self_improvement", None), "diff_generator", None),
        )
        return next((cand for cand in candidates if cand is not None), None)

    @staticmethod
    def resolve_patch_applier(runtime_core: Any) -> Any:
        scan_service = getattr(runtime_core, "self_improvement", None)
        repair_service = getattr(runtime_core, "self_improvement_service", None)
        repair_adapter = getattr(repair_service, "runtime_adapter", None)

        candidates = (
            getattr(runtime_core, "patch_applier", None),
            getattr(runtime_core, "apply_changes", None),
            getattr(scan_service, "patch_applier", None),
            getattr(scan_service, "apply_changes", None),
            getattr(scan_service, "apply_patch", None),
            getattr(repair_service, "patch_applier", None),
            getattr(repair_service, "apply_changes", None),
            getattr(repair_service, "apply_patch", None),
            getattr(repair_adapter, "patch_applier", None),
            getattr(repair_adapter, "apply_changes", None),
            getattr(repair_adapter, "apply_patch", None),
        )

        for candidate in candidates:
            if candidate is not None:
                return candidate

        try:
            from buster.ui.v9.panels.self_improvement.patch_applier import PatchApplier
            return PatchApplier(project_root=getattr(runtime_core, "root", "."))
        except Exception:
            return None