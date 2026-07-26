from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Hurdle:
    hurdle_id: str
    error_type: str
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
    stack_trace: str
    code_context: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


class HurdleClassifier:
    """Classifies exceptions and system failures into structured Hurdle objects with source context."""

    def __init__(self, project_root: str | Path = ".", context_lines: int = 5) -> None:
        self.project_root = Path(project_root).resolve()
        self.context_lines = context_lines

    def classify_exception(
        self,
        exc: Exception,
        file_path: Optional[str | Path] = None,
        line_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Hurdle:
        """Converts a live Python exception into a structured Hurdle."""
        error_type = type(exc).__name__
        message = str(exc)
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        # Extract file and line from traceback if not explicitly provided
        if not file_path or not line_number:
            extracted = self._extract_frame_info(exc)
            file_path = file_path or extracted.get("file_path")
            line_number = line_number or extracted.get("line_number")

        norm_path = str(file_path) if file_path else None
        code_context = self._extract_code_context(norm_path, line_number)

        hurdle_id = f"hurdle_{hash((error_type, message, norm_path, line_number)) & 0xFFFFFF:06x}"

        return Hurdle(
            hurdle_id=hurdle_id,
            error_type=error_type,
            message=message,
            file_path=norm_path,
            line_number=line_number,
            stack_trace=tb_str,
            code_context=code_context,
            metadata=metadata or {},
        )

    def _extract_frame_info(self, exc: Exception) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        tb = exc.__traceback__
        while tb:
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            # Filter for project files
            if str(self.project_root) in filename or not filename.startswith("<"):
                info["file_path"] = filename
                info["line_number"] = tb.tb_lineno
            tb = tb.tb_next
        return info

    def _extract_code_context(
        self, file_path: Optional[str], line_number: Optional[int]
    ) -> List[str]:
        if not file_path or not line_number:
            return []

        path = Path(file_path)
        if not path.is_absolute():
            path = self.project_root / path

        if not path.exists() or not path.is_file():
            return []

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            start = max(0, line_number - 1 - self.context_lines)
            end = min(len(lines), line_number + self.context_lines)
            return lines[start:end]
        except Exception as e:
            logger.warning(f"Could not read code context from {path}: {e}")
            return []