from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from .backup_manager import BackupManager
from .change_manifest import ChangeManifest, FileChangeRecord


@dataclass(slots=True)
class RollbackFileResult:
    path: str
    success: bool
    action: str
    message: str = ""
    restored_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "restored_hash": self.restored_hash,
        }


@dataclass(slots=True)
class RollbackResult:
    success: bool
    change_id: str
    restored_files: int = 0
    removed_files: int = 0
    failed_files: int = 0
    files: list[RollbackFileResult] | None = None
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "change_id": self.change_id,
            "restored_files": self.restored_files,
            "removed_files": self.removed_files,
            "failed_files": self.failed_files,
            "files": [
                item.to_dict()
                for item in (self.files or [])
            ],
            "errors": list(self.errors or []),
        }


class RollbackManager:
    """
    Restore a previously applied change from ChangeManifest backups.

    Existing files are restored from their recorded backup paths.
    Files that did not exist before apply are removed during rollback.
    """

    def __init__(
        self,
        project_root: str | Path,
        history_root: str | Path | None = None,
        backup_manager: Optional[BackupManager] = None,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.backup_manager = backup_manager or BackupManager(
            project_root=self.project_root,
            history_root=history_root,
        )

    def rollback(
        self,
        manifest: ChangeManifest | Mapping[str, Any] | str,
        *,
        verify: bool = True,
        save_manifest: bool = True,
    ) -> RollbackResult:
        manifest = self._resolve_manifest(manifest)
        manifest.mark_rollback_started()

        file_results: list[RollbackFileResult] = []
        errors: list[str] = []

        restored_files = 0
        removed_files = 0
        failed_files = 0

        for record in manifest.files:
            try:
                result = self._rollback_file(
                    record,
                    verify=verify,
                )
                file_results.append(result)

                if result.success:
                    if result.action == "restored":
                        restored_files += 1
                    elif result.action == "removed":
                        removed_files += 1
                else:
                    failed_files += 1
                    errors.append(
                        result.message
                        or f"Rollback failed for {record.path}"
                    )

            except Exception as exc:
                failed_files += 1
                message = f"{record.path}: {exc}"
                errors.append(message)
                file_results.append(
                    RollbackFileResult(
                        path=record.path,
                        success=False,
                        action="failed",
                        message=message,
                    )
                )

        success = failed_files == 0

        result = RollbackResult(
            success=success,
            change_id=manifest.change_id,
            restored_files=restored_files,
            removed_files=removed_files,
            failed_files=failed_files,
            files=file_results,
            errors=errors,
        )

        if success:
            manifest.mark_rolled_back(result.to_dict())
        else:
            manifest.mark_rollback_failed(
                "\n".join(errors)
            )
            manifest.rollback = result.to_dict()

        if save_manifest:
            self.backup_manager.save_manifest(manifest)

        return result

    def rollback_change(
        self,
        change_id: str,
        *,
        verify: bool = True,
    ) -> RollbackResult:
        return self.rollback(
            change_id,
            verify=verify,
            save_manifest=True,
        )

    def can_rollback(
        self,
        manifest: ChangeManifest | Mapping[str, Any] | str,
    ) -> bool:
        try:
            resolved = self._resolve_manifest(manifest)
        except Exception:
            return False

        if not resolved.can_rollback:
            return False

        for record in resolved.files:
            if record.existed_before:
                if not record.backup_path:
                    return False

                backup = Path(record.backup_path)
                if not backup.exists() or not backup.is_file():
                    return False

        return True

    def verify_restored_state(
        self,
        manifest: ChangeManifest | Mapping[str, Any] | str,
    ) -> dict[str, Any]:
        manifest = self._resolve_manifest(manifest)

        errors: list[str] = []
        verified = 0
        removed = 0

        for record in manifest.files:
            target = Path(record.path)

            if record.existed_before:
                if not target.exists() or not target.is_file():
                    errors.append(
                        f"Restored file is missing: {target}"
                    )
                    continue

                content = target.read_bytes()
                digest = FileChangeRecord.hash_bytes(content)

                if digest != record.original_hash:
                    errors.append(
                        f"Restored hash mismatch: {target}"
                    )
                    continue

                if len(content) != record.original_size:
                    errors.append(
                        f"Restored size mismatch: {target}"
                    )
                    continue

                verified += 1
                continue

            if target.exists():
                errors.append(
                    f"Rollback should have removed: {target}"
                )
                continue

            removed += 1

        return {
            "success": not errors,
            "change_id": manifest.change_id,
            "verified_files": verified,
            "removed_files": removed,
            "errors": errors,
        }

    def _resolve_manifest(
        self,
        value: ChangeManifest | Mapping[str, Any] | str,
    ) -> ChangeManifest:
        if isinstance(value, ChangeManifest):
            return value

        if isinstance(value, Mapping):
            return ChangeManifest.from_value(value)

        if isinstance(value, str):
            candidate = Path(value)

            if candidate.exists() and candidate.is_file():
                return ChangeManifest.load(candidate)

            return self.backup_manager.load_manifest(value)

        raise TypeError(
            "Rollback requires a ChangeManifest, mapping, "
            "manifest path, or change ID."
        )

    def _rollback_file(
        self,
        record: FileChangeRecord,
        *,
        verify: bool,
    ) -> RollbackFileResult:
        target = Path(record.path)

        if record.existed_before:
            return self._restore_existing_file(
                record=record,
                target=target,
                verify=verify,
            )

        return self._remove_new_file(
            record=record,
            target=target,
        )

    def _restore_existing_file(
        self,
        record: FileChangeRecord,
        target: Path,
        *,
        verify: bool,
    ) -> RollbackFileResult:
        if not record.backup_path:
            return RollbackFileResult(
                path=record.path,
                success=False,
                action="failed",
                message=(
                    "No backup path was recorded for "
                    f"{record.path}"
                ),
            )

        backup = Path(record.backup_path)

        if not backup.exists() or not backup.is_file():
            return RollbackFileResult(
                path=record.path,
                success=False,
                action="failed",
                message=f"Backup file is missing: {backup}",
            )

        backup_content = backup.read_bytes()
        backup_hash = FileChangeRecord.hash_bytes(
            backup_content
        )

        if (
            record.original_hash
            and backup_hash != record.original_hash
        ):
            return RollbackFileResult(
                path=record.path,
                success=False,
                action="failed",
                message=(
                    "Backup integrity check failed for "
                    f"{record.path}"
                ),
            )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = target.with_name(
            target.name + ".rollback_tmp"
        )

        if temp.exists():
            temp.unlink()

        shutil.copy2(backup, temp)
        os.replace(temp, target)

        restored_content = target.read_bytes()
        restored_hash = FileChangeRecord.hash_bytes(
            restored_content
        )

        if verify:
            if (
                record.original_hash
                and restored_hash != record.original_hash
            ):
                return RollbackFileResult(
                    path=record.path,
                    success=False,
                    action="failed",
                    message=(
                        "Restored hash does not match original "
                        f"for {record.path}"
                    ),
                    restored_hash=restored_hash,
                )

            if len(restored_content) != record.original_size:
                return RollbackFileResult(
                    path=record.path,
                    success=False,
                    action="failed",
                    message=(
                        "Restored size does not match original "
                        f"for {record.path}"
                    ),
                    restored_hash=restored_hash,
                )

        record.status = "rolled_back"
        record.modified_hash = restored_hash
        record.modified_size = len(restored_content)
        record.exists_after = True
        record.error = ""

        return RollbackFileResult(
            path=record.path,
            success=True,
            action="restored",
            message="Original file restored.",
            restored_hash=restored_hash,
        )

    def _remove_new_file(
        self,
        record: FileChangeRecord,
        target: Path,
    ) -> RollbackFileResult:
        if not target.exists():
            record.status = "rolled_back"
            record.exists_after = False
            record.modified_hash = ""
            record.modified_size = 0
            record.error = ""

            return RollbackFileResult(
                path=record.path,
                success=True,
                action="removed",
                message="Generated file was already absent.",
            )

        if target.is_dir():
            return RollbackFileResult(
                path=record.path,
                success=False,
                action="failed",
                message=(
                    "Rollback refused to remove a directory: "
                    f"{target}"
                ),
            )

        target.unlink()

        record.status = "rolled_back"
        record.exists_after = False
        record.modified_hash = ""
        record.modified_size = 0
        record.error = ""

        return RollbackFileResult(
            path=record.path,
            success=True,
            action="removed",
            message="Generated file removed.",
        )


__all__ = [
    "RollbackFileResult",
    "RollbackManager",
    "RollbackResult",
]
