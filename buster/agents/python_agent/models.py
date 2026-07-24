from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class QualityMetrics:
    syntax_ok: bool = False
    compile_ok: bool = False
    class_retention: float = 1.0  # 0.0 to 1.0
    function_retention: float = 1.0
    size_ratio: float = 1.0
    overall_score: float = 0.0  # 0 to 100

    def is_acceptable(self, threshold: float = 50.0) -> bool:
        return self.overall_score >= threshold


@dataclass
class AgentRequest:
    file_path: str
    original_code: str
    instruction: str
    context_files: Dict[str, str] = field(default_factory=dict)


@dataclass
class PreviewDiff:
    file_path: str
    original_code: str
    proposed_code: str
    diff_text: str
    quality: QualityMetrics
    success: bool
    error_message: Optional[str] = None