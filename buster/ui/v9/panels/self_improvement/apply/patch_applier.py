from __future__ import annotations

import os
import py_compile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .backup_manager import BackupManager
from .change_manifest import ChangeManifest, FileChangeRecord
from .preview_diff_panel import PreviewDiff
from .protected_files import ProtectedFileError, find_protected_paths


@dataclass(slots=True)
class ApplyFileResult:
    path: str
    success: bool
    action: str
    message: str = ""
    original_hash: str = ""
    modified_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "original_hash": self.original_hash,
            "modified_hash": self.modified_hash,
        }


@dataclass(slots=True)
class ApplyResult:
    success: bool
    change_id: str
    message: str
    applied_files: int = 0
    failed_files: int = 0
    manifest_path: str = ""
    backup_root: str = ""
    files: list[ApplyFileResult] | None = None
    errors: list[str] | None = None
    rolled_back: bool = False
    protected_files: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "change_id": self.change_id,
            "message": self.message,
            "applied_files": self.applied_files,
            "failed_files": self.failed_files,
            "manifest_path": self.manifest_path,
            "backup_root": self.backup_root,
            "files": [
                item.to_dict()
                for item in (self.files or [])
            ],
            "errors": list(self.errors or []),
            "rolled_back": self.rolled_back,
            "protected_files": list(self.protected_files or []),
        }


@dataclass(slots=True)
class _PatchFile:
    old_path: str
    new_path: str
    hunks: list["_Hunk"]

    @property
    def is_new(self) -> bool:
        return self.old_path == "/dev/null"

    @property
    def is_deleted(self) -> bool:
        return self.new_path == "/dev/null"

    @property
    def target_path(self) -> str:
        return self.old_path if self.is_deleted else self.new_path


@dataclass(slots=True)
class _Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


class PatchApplier:
    """
    Safe unified-diff applier for the Self Improvement workflow.

    Supported entry points:
        apply(preview, ...)
        apply_patch(preview, ...)
        run(preview, ...)

    Before changing files, it creates a ChangeManifest and durable backups.
    Paths are restricted to project_root.
    """

    _HUNK_RE = re.compile(
        r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
        r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
    )

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
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def apply(
        self,
        preview: PreviewDiff | Mapping[str, Any] | str,
        backup: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        allow_protected: bool = False,
    ) -> ApplyResult:
        self._cancelled = False
        preview = PreviewDiff.from_value(preview)

        if not preview.patch.strip():
            raise RuntimeError("Cannot apply an empty patch.")

        self._progress(progress_callback, 5, "Parsing patch...")
        patch_files = self._parse_patch(preview.patch)

        if not patch_files:
            raise RuntimeError(
                "The generated patch contains no supported unified-diff file sections."
            )

        target_paths = [
            self._resolve_target(item.target_path)
            for item in patch_files
        ]

        protected_paths = find_protected_paths(
            target_paths,
            project_root=self.project_root,
        )
        if protected_paths and not allow_protected:
            relative = [
                path.relative_to(self.project_root).as_posix()
                for path in protected_paths
            ]
            raise ProtectedFileError(
                "Protected file change blocked. Explicit approval is required: "
                + ", ".join(relative)
            )

        # Safety backups are mandatory. The argument remains for API
        # compatibility, but callers cannot disable recovery protection.
        backup = True

        manifest = ChangeManifest.create(
            project_root=self.project_root,
            title=preview.title,
            summary=preview.summary,
            patch=preview.patch,
            files=[
                FileChangeRecord.inspect_file(path)
                for path in target_paths
            ],
            requested_from=str(
                preview.metadata.get("requested_from", "self_improvement")
            ),
            approval_required=True,
            metadata={
                **dict(preview.metadata),
                "file_path": preview.file_path,
                "changed_files": len(patch_files),
            },
        )
        manifest.approve()

        backup_root = ""
        manifest_path = ""

        if backup:
            self._progress(progress_callback, 15, "Creating backup...")
            backup_result = self.backup_manager.create_backup(
                manifest,
                target_paths,
                fail_on_missing=False,
            )

            if not backup_result.success:
                raise RuntimeError(
                    "Backup failed: "
                    + "; ".join(backup_result.errors or [])
                )

            backup_root = backup_result.backup_root
            manifest_path = backup_result.manifest_path
            manifest = self.backup_manager.load_manifest(
                manifest.change_id
            )

        manifest.mark_apply_started()
        manifest_path = str(
            self.backup_manager.save_manifest(manifest)
        )

        file_results: list[ApplyFileResult] = []
        errors: list[str] = []
        recovery_state = self._capture_recovery_state(target_paths)
        rolled_back = False

        try:
            total = len(patch_files)

            for index, patch_file in enumerate(patch_files, start=1):
                if self._cancelled:
                    raise RuntimeError("Patch application cancelled.")

                target = self._resolve_target(patch_file.target_path)
                percent = 20 + int((index - 1) / max(total, 1) * 65)
                self._progress(
                    progress_callback,
                    percent,
                    f"Applying {target.name}...",
                )

                try:
                    result = self._apply_file(
                        patch_file=patch_file,
                        target=target,
                    )

                    if target.suffix.lower() == ".py" and target.exists():
                        self._progress(
                            progress_callback,
                            min(94, percent + 5),
                            f"Compiling {target.name}...",
                        )
                        py_compile.compile(
                            str(target),
                            doraise=True,
                        )

                    file_results.append(result)

                    record = manifest.get_file(str(target))
                    if record is None:
                        record = manifest.add_file(
                            FileChangeRecord.inspect_file(target)
                        )

                    record.capture_modified_state(target)
                    record.status = "applied"
                    record.error = ""

                except Exception as exc:
                    message = f"{target}: {exc}"
                    errors.append(message)
                    file_results.append(
                        ApplyFileResult(
                            path=str(target),
                            success=False,
                            action="failed",
                            message=message,
                        )
                    )

                    record = manifest.get_file(str(target))
                    if record is not None:
                        record.status = "failed"
                        record.error = str(exc)

                    raise

            manifest.mark_applied()
            manifest_path = str(
                self.backup_manager.save_manifest(manifest)
            )

            self._progress(progress_callback, 100, "Changes applied.")

            return ApplyResult(
                success=True,
                change_id=manifest.change_id,
                message="Changes applied successfully.",
                applied_files=len(file_results),
                failed_files=0,
                manifest_path=manifest_path,
                backup_root=backup_root,
                files=file_results,
                errors=[],
                rolled_back=False,
                protected_files=[
                    path.relative_to(self.project_root).as_posix()
                    for path in protected_paths
                ],
            )

        except Exception as exc:
            try:
                self._progress(
                    progress_callback,
                    96,
                    "Apply failed. Restoring original files...",
                )
                self._restore_recovery_state(recovery_state)
                rolled_back = True
            except Exception as rollback_exc:
                errors.append(f"Automatic rollback failed: {rollback_exc}")

            manifest.mark_apply_failed(
                f"{exc} | rolled_back={rolled_back}"
            )
            manifest_path = str(
                self.backup_manager.save_manifest(manifest)
            )

            return ApplyResult(
                success=False,
                change_id=manifest.change_id,
                message=str(exc),
                applied_files=sum(
                    1 for item in file_results if item.success
                ),
                failed_files=max(
                    1,
                    sum(1 for item in file_results if not item.success),
                ),
                manifest_path=manifest_path,
                backup_root=backup_root,
                files=file_results,
                errors=errors or [str(exc)],
                rolled_back=rolled_back,
                protected_files=[
                    path.relative_to(self.project_root).as_posix()
                    for path in protected_paths
                ],
            )

    def apply_patch(
        self,
        preview: PreviewDiff | Mapping[str, Any] | str,
        backup: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        allow_protected: bool = False,
    ) -> ApplyResult:
        return self.apply(
            preview=preview,
            backup=backup,
            progress_callback=progress_callback,
            allow_protected=allow_protected,
        )

    def run(
        self,
        preview: PreviewDiff | Mapping[str, Any] | str,
        backup: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        allow_protected: bool = False,
    ) -> ApplyResult:
        return self.apply(
            preview=preview,
            backup=backup,
            progress_callback=progress_callback,
            allow_protected=allow_protected,
        )

    @staticmethod
    def _capture_recovery_state(
        target_paths: list[Path],
    ) -> dict[Path, bytes | None]:
        """Capture exact pre-apply state for guaranteed local rollback."""
        state: dict[Path, bytes | None] = {}
        for path in target_paths:
            state[path] = path.read_bytes() if path.is_file() else None
        return state

    @staticmethod
    def _restore_recovery_state(
        recovery_state: Mapping[Path, bytes | None],
    ) -> None:
        """Restore files exactly as they were before the apply attempt."""
        failures: list[str] = []

        for path, original in recovery_state.items():
            try:
                if original is None:
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                        else:
                            raise RuntimeError(
                                f"Cannot remove non-file rollback target: {path}"
                            )
                    continue

                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(path.name + ".buster_rollback_tmp")
                temp.write_bytes(original)
                os.replace(temp, path)
            except Exception as exc:
                failures.append(f"{path}: {exc}")

        if failures:
            raise RuntimeError("; ".join(failures))

    def _apply_file(
        self,
        patch_file: _PatchFile,
        target: Path,
    ) -> ApplyFileResult:
        existed_before = target.exists() and target.is_file()
        original = target.read_bytes() if existed_before else b""
        original_hash = FileChangeRecord.hash_bytes(original) if existed_before else ""

        if patch_file.is_deleted:
            if not existed_before:
                raise FileNotFoundError(
                    f"Cannot delete missing file: {target}"
                )

            target.unlink()
            return ApplyFileResult(
                path=str(target),
                success=True,
                action="deleted",
                message="File deleted.",
                original_hash=original_hash,
                modified_hash="",
            )

        old_text = (
            original.decode("utf-8-sig")
            if existed_before
            else ""
        )
        old_lines = old_text.splitlines(keepends=True)

        new_lines = self._apply_hunks(
            old_lines=old_lines,
            hunks=patch_file.hunks,
        )
        new_text = "".join(new_lines)
        new_bytes = new_text.encode("utf-8")

        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".buster_apply_tmp")
        temp.write_bytes(new_bytes)
        os.replace(temp, target)

        modified_hash = FileChangeRecord.hash_bytes(new_bytes)

        return ApplyFileResult(
            path=str(target),
            success=True,
            action="created" if patch_file.is_new else "modified",
            message=(
                "File created."
                if patch_file.is_new
                else "File updated."
            ),
            original_hash=original_hash,
            modified_hash=modified_hash,
        )

    def _apply_hunks(
        self,
        old_lines: list[str],
        hunks: list[_Hunk],
    ) -> list[str]:
        result: list[str] = []
        source_index = 0

        for hunk in hunks:
            expected_index = max(0, hunk.old_start - 1)

            if expected_index < source_index:
                raise RuntimeError(
                    "Patch hunks overlap or are out of order."
                )

            result.extend(old_lines[source_index:expected_index])
            source_index = expected_index

            for line in hunk.lines:
                if not line:
                    prefix = " "
                    value = ""
                else:
                    prefix = line[0]
                    value = line[1:]

                if prefix == "\\":
                    continue

                if prefix == " ":
                    self._require_source_line(
                        old_lines,
                        source_index,
                        value,
                        "context",
                    )
                    result.append(old_lines[source_index])
                    source_index += 1
                    continue

                if prefix == "-":
                    self._require_source_line(
                        old_lines,
                        source_index,
                        value,
                        "removed",
                    )
                    source_index += 1
                    continue

                if prefix == "+":
                    result.append(value)
                    continue

                raise RuntimeError(
                    f"Unsupported patch line prefix: {prefix!r}"
                )

        result.extend(old_lines[source_index:])
        return result

    @staticmethod
    def _require_source_line(
        old_lines: list[str],
        index: int,
        expected: str,
        kind: str,
    ) -> None:
        if index >= len(old_lines):
            raise RuntimeError(
                f"Patch {kind} line exceeds end of file."
            )

        actual = old_lines[index]

        if actual.rstrip("\r\n") != expected.rstrip("\r\n"):
            raise RuntimeError(
                f"Patch {kind} mismatch at source line {index + 1}. "
                f"Expected {expected.rstrip()!r}, "
                f"found {actual.rstrip()!r}."
            )

    def _parse_patch(self, patch: str) -> list[_PatchFile]:
        lines = patch.splitlines(keepends=True)
        files: list[_PatchFile] = []
        index = 0

        while index < len(lines):
            line = lines[index]

            if line.startswith("diff --git "):
                index += 1
                continue

            if not line.startswith("--- "):
                index += 1
                continue

            old_path = self._clean_header_path(line[4:])
            index += 1

            if index >= len(lines) or not lines[index].startswith("+++ "):
                raise RuntimeError(
                    "Malformed unified diff: missing +++ file header."
                )

            new_path = self._clean_header_path(lines[index][4:])
            index += 1
            hunks: list[_Hunk] = []

            while index < len(lines):
                current = lines[index]

                if current.startswith("diff --git ") or current.startswith("--- "):
                    break

                match = self._HUNK_RE.match(current.rstrip("\r\n"))
                if not match:
                    index += 1
                    continue

                old_start = int(match.group("old_start"))
                old_count = int(match.group("old_count") or 1)
                new_start = int(match.group("new_start"))
                new_count = int(match.group("new_count") or 1)
                index += 1

                hunk_lines: list[str] = []

                while index < len(lines):
                    candidate = lines[index]

                    if (
                        candidate.startswith("@@ ")
                        or candidate.startswith("diff --git ")
                        or candidate.startswith("--- ")
                    ):
                        break

                    if candidate.startswith(
                        (" ", "+", "-", "\\")
                    ):
                        hunk_lines.append(candidate)

                    index += 1

                hunks.append(
                    _Hunk(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        lines=hunk_lines,
                    )
                )

            files.append(
                _PatchFile(
                    old_path=old_path,
                    new_path=new_path,
                    hunks=hunks,
                )
            )

        return files

    def _resolve_target(self, value: str) -> Path:
        cleaned = self._strip_git_prefix(value)

        if cleaned in {"", "/dev/null"}:
            raise RuntimeError(
                "Patch does not identify a valid target path."
            )

        candidate = Path(cleaned).expanduser()

        if not candidate.is_absolute():
            candidate = self.project_root / candidate

        resolved = candidate.resolve()

        try:
            resolved.relative_to(self.project_root)
        except ValueError as exc:
            raise RuntimeError(
                f"Patch target is outside project root: {resolved}"
            ) from exc

        return resolved

    @staticmethod
    def _clean_header_path(value: str) -> str:
        return value.strip().split("\t", 1)[0]

    @staticmethod
    def _strip_git_prefix(value: str) -> str:
        normalized = value.replace("\\", "/").strip()

        if normalized.startswith("a/") or normalized.startswith("b/"):
            normalized = normalized[2:]

        return normalized

    @staticmethod
    def _progress(
        callback: Optional[Callable[[int, str], None]],
        value: int,
        message: str,
    ) -> None:
        if callback is None:
            return

        try:
            callback(int(value), str(message))
        except Exception:
            pass


__all__ = [
    "ApplyFileResult",
    "ApplyResult",
    "PatchApplier",
]
