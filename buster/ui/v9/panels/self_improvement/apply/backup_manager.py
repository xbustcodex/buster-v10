from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from .change_manifest import ChangeManifest, FileChangeRecord


@dataclass(slots=True)
class BackupResult:
    success: bool
    change_id: str
    backup_root: str
    manifest_path: str
    files_backed_up: int = 0
    files_missing: int = 0
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "change_id": self.change_id,
            "backup_root": self.backup_root,
            "manifest_path": self.manifest_path,
            "files_backed_up": self.files_backed_up,
            "files_missing": self.files_missing,
            "errors": list(self.errors or []),
        }


class BackupManager:
    """
    Create durable per-change backups before a patch is applied.

    Directory structure:

        <history_root>/
        ├── manifests/
        │   └── <change_id>.json
        └── backups/
            └── <change_id>/
                ├── files/
                │   └── <project-relative paths>
                └── metadata.json

    Files outside project_root are stored under an ``external`` namespace.
    """

    def __init__(
        self,
        project_root: str | Path,
        history_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

        self.history_root = (
            Path(history_root).expanduser().resolve()
            if history_root
            else self.project_root / "data" / "self_improvement"
        )

        self.manifests_root = self.history_root / "manifests"
        self.backups_root = self.history_root / "backups"

        self.manifests_root.mkdir(parents=True, exist_ok=True)
        self.backups_root.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        manifest: ChangeManifest | Mapping[str, Any],
        file_paths: Optional[Iterable[str | Path]] = None,
        *,
        fail_on_missing: bool = False,
        overwrite: bool = False,
    ) -> BackupResult:
        manifest = ChangeManifest.from_value(manifest)

        if not manifest.project_root:
            manifest.project_root = str(self.project_root)

        errors: list[str] = []
        files_backed_up = 0
        files_missing = 0

        backup_root = self.backup_directory(manifest.change_id)
        files_root = backup_root / "files"

        if backup_root.exists() and not overwrite:
            existing = self.manifest_path(manifest.change_id)

            if existing.exists():
                loaded = ChangeManifest.load(existing)
                return BackupResult(
                    success=True,
                    change_id=loaded.change_id,
                    backup_root=str(backup_root),
                    manifest_path=str(existing),
                    files_backed_up=sum(
                        1
                        for record in loaded.files
                        if record.backup_path
                    ),
                    files_missing=sum(
                        1
                        for record in loaded.files
                        if not record.existed_before
                    ),
                    errors=[],
                )

            raise FileExistsError(
                f"Backup directory already exists: {backup_root}"
            )

        if overwrite and backup_root.exists():
            shutil.rmtree(backup_root)

        files_root.mkdir(parents=True, exist_ok=True)

        targets = self._resolve_targets(
            manifest=manifest,
            file_paths=file_paths,
        )

        if not targets:
            raise RuntimeError(
                "No target files were provided for backup."
            )

        manifest.files.clear()

        for target in targets:
            try:
                record = self._backup_one(
                    target=target,
                    files_root=files_root,
                )
                manifest.add_file(record)

                if record.existed_before:
                    files_backed_up += 1
                else:
                    files_missing += 1

                    if fail_on_missing:
                        errors.append(
                            f"Target file does not exist: {target}"
                        )

            except Exception as exc:
                errors.append(f"{target}: {exc}")

                manifest.add_file(
                    FileChangeRecord(
                        path=str(target),
                        existed_before=target.exists(),
                        exists_after=target.exists(),
                        status="backup_failed",
                        error=str(exc),
                    )
                )

        metadata = {
            "change_id": manifest.change_id,
            "project_root": str(self.project_root),
            "backup_root": str(backup_root),
            "files_backed_up": files_backed_up,
            "files_missing": files_missing,
            "errors": errors,
        }

        self._write_json_atomic(
            backup_root / "metadata.json",
            metadata,
        )

        if errors:
            manifest.status = "backup_failed"
            manifest.error = "\n".join(errors)
            manifest.touch()
        else:
            for record in manifest.files:
                if record.existed_before:
                    record.status = "backed_up"
                else:
                    record.status = "missing_before_apply"

            manifest.mark_backup_created()

        manifest_path = self.save_manifest(manifest)

        return BackupResult(
            success=not errors,
            change_id=manifest.change_id,
            backup_root=str(backup_root),
            manifest_path=str(manifest_path),
            files_backed_up=files_backed_up,
            files_missing=files_missing,
            errors=errors,
        )

    def save_manifest(
        self,
        manifest: ChangeManifest | Mapping[str, Any],
    ) -> Path:
        manifest = ChangeManifest.from_value(manifest)
        return manifest.save(
            self.manifest_path(manifest.change_id)
        )

    def load_manifest(
        self,
        change_id: str,
    ) -> ChangeManifest:
        return ChangeManifest.load(
            self.manifest_path(change_id)
        )

    def backup_directory(
        self,
        change_id: str,
    ) -> Path:
        return self.backups_root / str(change_id)

    def manifest_path(
        self,
        change_id: str,
    ) -> Path:
        return self.manifests_root / f"{change_id}.json"

    def backup_exists(
        self,
        change_id: str,
    ) -> bool:
        return (
            self.backup_directory(change_id).exists()
            and self.manifest_path(change_id).exists()
        )

    def remove_backup(
        self,
        change_id: str,
        *,
        remove_manifest: bool = False,
    ) -> None:
        backup_root = self.backup_directory(change_id)

        if backup_root.exists():
            shutil.rmtree(backup_root)

        if remove_manifest:
            manifest_path = self.manifest_path(change_id)

            if manifest_path.exists():
                manifest_path.unlink()

    def verify_backup(
        self,
        manifest: ChangeManifest | Mapping[str, Any],
    ) -> dict[str, Any]:
        manifest = ChangeManifest.from_value(manifest)

        errors: list[str] = []
        verified = 0
        intentionally_missing = 0

        for record in manifest.files:
            if not record.existed_before:
                intentionally_missing += 1
                continue

            if not record.backup_path:
                errors.append(
                    f"No backup path recorded for {record.path}"
                )
                continue

            backup = Path(record.backup_path)

            if not backup.exists() or not backup.is_file():
                errors.append(
                    f"Backup file is missing: {backup}"
                )
                continue

            content = backup.read_bytes()
            digest = FileChangeRecord.hash_bytes(content)

            if digest != record.original_hash:
                errors.append(
                    f"Backup hash mismatch for {record.path}"
                )
                continue

            if len(content) != record.original_size:
                errors.append(
                    f"Backup size mismatch for {record.path}"
                )
                continue

            verified += 1

        return {
            "success": not errors,
            "change_id": manifest.change_id,
            "verified_files": verified,
            "intentionally_missing": intentionally_missing,
            "errors": errors,
        }

    def _resolve_targets(
        self,
        manifest: ChangeManifest,
        file_paths: Optional[Iterable[str | Path]],
    ) -> list[Path]:
        values: list[str | Path] = []

        if file_paths is not None:
            values.extend(file_paths)

        if not values:
            values.extend(
                record.path
                for record in manifest.files
                if record.path
            )

        if not values:
            for mapping in (
                manifest.plan,
                manifest.finding,
                manifest.metadata,
            ):
                value = (
                    mapping.get("file_path")
                    or mapping.get("file")
                )

                if value:
                    values.append(value)

        targets: list[Path] = []
        seen: set[str] = set()

        for value in values:
            target = Path(value).expanduser()

            if not target.is_absolute():
                target = self.project_root / target

            target = target.resolve()
            key = os.path.normcase(str(target))

            if key in seen:
                continue

            seen.add(key)
            targets.append(target)

        return targets

    def _backup_one(
        self,
        target: Path,
        files_root: Path,
    ) -> FileChangeRecord:
        exists = target.exists() and target.is_file()

        backup_path = self._backup_path_for(
            target=target,
            files_root=files_root,
        )

        if not exists:
            return FileChangeRecord(
                path=str(target),
                backup_path="",
                original_hash="",
                original_size=0,
                existed_before=False,
                exists_after=False,
                status="missing_before_apply",
                metadata={
                    "relative_path": self._relative_label(target),
                },
            )

        backup_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(target, backup_path)

        content = target.read_bytes()
        backup_content = backup_path.read_bytes()

        source_hash = FileChangeRecord.hash_bytes(content)
        backup_hash = FileChangeRecord.hash_bytes(
            backup_content
        )

        if source_hash != backup_hash:
            raise RuntimeError(
                "Backup integrity verification failed."
            )

        return FileChangeRecord(
            path=str(target),
            backup_path=str(backup_path),
            original_hash=source_hash,
            original_size=len(content),
            existed_before=True,
            exists_after=True,
            status="backed_up",
            metadata={
                "relative_path": self._relative_label(target),
                "mode": target.stat().st_mode,
                "mtime_ns": target.stat().st_mtime_ns,
            },
        )

    def _backup_path_for(
        self,
        target: Path,
        files_root: Path,
    ) -> Path:
        try:
            relative = target.relative_to(self.project_root)
            return files_root / relative
        except ValueError:
            drive = (
                target.drive.replace(":", "")
                if target.drive
                else "root"
            )

            parts = [
                part
                for part in target.parts
                if part not in {
                    target.anchor,
                    target.drive,
                    "\\",
                    "/",
                }
            ]

            return (
                files_root
                / "external"
                / drive
                / Path(*parts)
            )

    def _relative_label(
        self,
        target: Path,
    ) -> str:
        try:
            return str(
                target.relative_to(self.project_root)
            ).replace("\\", "/")
        except ValueError:
            return str(target).replace("\\", "/")

    @staticmethod
    def _write_json_atomic(
        path: Path,
        payload: Mapping[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = path.with_suffix(
            path.suffix + ".tmp"
        )
        temp.write_text(
            json.dumps(
                dict(payload),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temp.replace(path)


__all__ = [
    "BackupManager",
    "BackupResult",
]
