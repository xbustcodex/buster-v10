from .models import UpgradePlan


class UpgradePlanner:
    def __init__(self, current_version: str):
        self.current_version = current_version

    def create_plan(self, manifest: dict) -> UpgradePlan:
        operations = manifest.get("operations", [])
        target_version = manifest.get("version", self.current_version)

        update_count = sum(1 for op in operations if op.get("type") == "update_file")
        create_count = sum(1 for op in operations if op.get("type") in ["add_file", "create_folder"])
        delete_count = sum(1 for op in operations if op.get("type") == "delete_file")

        disk_required = max(1, len(operations) * 2)

        return UpgradePlan(
            from_version=self.current_version,
            to_version=target_version,
            operations=operations,
            files_to_update=update_count,
            files_to_delete=delete_count,
            files_to_create=create_count,
            disk_required=disk_required,
            rollback_available=True,
            components_affected=manifest.get("components", [])
        )
