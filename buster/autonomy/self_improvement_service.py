from __future__ import annotations

import ast
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from buster.autonomy.engine import AutonomyEngine
from buster.autonomy.execution_engine import ExecutionEngine
from buster.autonomy.records import AutonomyJob
from buster.utils.datetime_utils import utc_timestamp


def utc_now() -> str:
    return utc_timestamp()


@dataclass
class ImprovementFinding:
    category: str
    title: str
    description: str
    severity: str = "low"
    file: str = ""
    line: int = 0
    confidence: float = 0.7
    suggested_request: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImprovementCycleResult:
    status: str
    mode: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    selected: Optional[Dict[str, Any]] = None
    job: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    message: str = ""
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SelfImprovementService:
    """Scan Buster for safe improvements and turn findings into autonomy jobs."""

    DEFAULT_EXCLUDES = {
        ".git", ".idea", ".venv", "venv", "__pycache__", "build", "dist",
        "data", "logs", "screenshots", "node_modules", "legacy_scripts",
    }
    SEVERITY_ORDER = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    CATEGORY_PRIORITY = {
        "syntax": 100,
        "tests": 90,
        "safety": 80,
        "architecture": 70,
        "performance": 60,
        "todo": 10,
    }
    TODO_PATTERN = re.compile(
        r"^\s*(?:#|//|<!--)\s*(TODO|FIXME|HACK|XXX)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        root: str | Path = ".",
        *,
        autonomy_engine: Optional[AutonomyEngine] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        runtime_core: Any = None,
        state_path: str | Path = "data/self_improvement_state.json",
        history_path: str | Path = "data/self_improvement_history.json",
        excludes: Optional[Iterable[str]] = None,
        max_findings: int = 100,
    ) -> None:
        self.root = Path(root).resolve()
        self.runtime_core = runtime_core
        self.autonomy_engine = autonomy_engine or AutonomyEngine(
            state_path=self.root / "data" / "autonomy_state.json",
            history_path=self.root / "data" / "autonomy_history.json",
        )
        self.execution_engine = execution_engine or ExecutionEngine(
            root=self.root,
            runtime_core=runtime_core,
            autonomy_engine=self.autonomy_engine,
        )
        self.state_path = self._resolve(state_path)
        self.history_path = self._resolve(history_path)
        self.excludes = set(excludes or self.DEFAULT_EXCLUDES)
        self.max_findings = max(1, int(max_findings))
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_files()

    def scan(self) -> List[ImprovementFinding]:
        findings: List[ImprovementFinding] = []
        findings.extend(self._scan_syntax())
        findings.extend(self._scan_todos())
        findings.extend(self._scan_large_modules())
        findings.extend(self._scan_tests())
        findings.extend(self._scan_git())
        findings = self._deduplicate(findings)
        findings = self._filter_ignored(findings)
        findings.sort(
            key=lambda item: (
                -self.CATEGORY_PRIORITY.get(item.category, 0),
                -self.SEVERITY_ORDER.get(item.severity, 0),
                -item.confidence,
                item.file,
                item.line,
            )
        )
        return findings[: self.max_findings]

    def run_cycle(
        self,
        *,
        mode: Optional[str] = None,
        auto_execute: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ImprovementCycleResult:
        state = self.load_state()
        active_mode = mode or state.get("mode", "manual")
        if active_mode not in {"manual", "assisted", "autonomous"}:
            raise ValueError("mode must be manual, assisted, or autonomous")

        result = ImprovementCycleResult(status="scanning", mode=active_mode)
        findings = self.scan()
        result.findings = [item.to_dict() for item in findings]

        if not findings:
            result.status = "idle"
            result.message = "No actionable improvement was found."
            return self._finish(result)

        selected = self.select_finding(findings)
        if selected is None:
            result.status = "idle"
            result.message = "Findings were detected but none passed the safety policy."
            return self._finish(result)

        result.selected = selected.to_dict()
        if active_mode == "manual":
            result.status = "proposal_ready"
            result.message = "Manual mode reports improvements without creating jobs."
            return self._finish(result)

        job = self.create_job(selected, context=context)
        result.job = job.to_dict()

        should_execute = active_mode == "autonomous" if auto_execute is None else bool(auto_execute)
        if active_mode == "assisted" or not should_execute:
            result.status = "awaiting_approval"
            result.message = "Improvement job created and waiting for approval."
            return self._finish(result)

        execution = self.execution_engine.execute(
            job,
            context={**dict(context or {}), "self_improvement": True, "finding": selected.to_dict()},
            mode="autonomous",
        )
        result.execution = execution.to_dict()
        result.status = execution.status
        result.message = "Self-improvement completed." if execution.success else "Self-improvement failed or was blocked."
        return self._finish(result)

    def select_finding(self, findings: Iterable[ImprovementFinding]) -> Optional[ImprovementFinding]:
        for finding in findings:
            if finding.severity == "critical":
                continue
            request = finding.suggested_request or finding.description
            preview = self.execution_engine.preview(
                request,
                project=self.root.name,
                project_type=self._project_type(),
                context={"self_improvement": True, "finding": finding.to_dict()},
            )
            if preview.get("risk", {}).get("level") == "low":
                return finding
        return None

    def create_job(
        self,
        finding: ImprovementFinding,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomyJob:
        request = finding.suggested_request or f"Improve Buster: {finding.title}. {finding.description}"
        return self.autonomy_engine.create_job(
            title=f"Self Improvement: {finding.title}",
            request=request,
            project=self.root.name,
            project_type=self._project_type(),
            context={
                **dict(context or {}),
                "self_improvement": True,
                "finding": finding.to_dict(),
                "has_tests": self._has_tests(),
                "error_count": 1 if finding.category in {"syntax", "tests"} else 0,
            },
        )

    def set_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in {"manual", "assisted", "autonomous"}:
            raise ValueError("mode must be manual, assisted, or autonomous")
        state = self.load_state()
        state.update({"mode": mode, "enabled": mode != "manual", "updated_at": utc_now()})
        self.save_state(state)
        try:
            self.autonomy_engine.set_mode(mode)
        except Exception:
            pass
        return state

    def status(self) -> Dict[str, Any]:
        state = self.load_state()
        history = self._history()
        return {
            "mode": state.get("mode", "manual"),
            "enabled": state.get("enabled", False),
            "last_cycle": state.get("last_cycle"),
            "cycles": len(history),
            "autonomy": self.autonomy_engine.status(),
            "execution": self.execution_engine.status(),
        }

    def load_state(self) -> Dict[str, Any]:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else self.default_state()
        except Exception:
            return self.default_state()

    def save_state(self, state: Mapping[str, Any]) -> None:
        payload = dict(state)
        payload["updated_at"] = utc_now()
        self.state_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def default_state(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "mode": "manual",
            "last_cycle": None,
            "ignored_findings": {},
            "updated_at": utc_now(),
        }

    def _scan_syntax(self) -> List[ImprovementFinding]:
        findings: List[ImprovementFinding] = []
        for path in self._python_files():
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                findings.append(
                    ImprovementFinding(
                        category="syntax",
                        title="Repair Python syntax error",
                        description=str(exc),
                        severity="high",
                        file=self._relative(path),
                        line=int(exc.lineno or 0),
                        confidence=0.99,
                        suggested_request=f"Fix the syntax error in {self._relative(path)} at line {exc.lineno or 0}, then run tests.",
                    )
                )
            except (OSError, UnicodeError):
                pass
        return findings

    def _scan_todos(self) -> List[ImprovementFinding]:
        """Find genuine TODO-style comments without matching code or strings."""
        findings: List[ImprovementFinding] = []

        for path in self._python_files():
            try:
                lines = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
            except OSError:
                continue

            for line_number, line in enumerate(lines, start=1):
                match = self.TODO_PATTERN.search(line)
                if not match:
                    continue

                marker = match.group(1).upper()
                relative = self._relative(path)

                findings.append(
                    ImprovementFinding(
                        category="todo",
                        title=f"Resolve {marker} marker",
                        description=line.strip(),
                        severity="low",
                        file=relative,
                        line=line_number,
                        confidence=0.9,
                        suggested_request=(
                            f"Review and safely resolve the {marker} in "
                            f"{relative} at line {line_number}. "
                            "Preserve behaviour and run tests."
                        ),
                        metadata={
                            "marker": marker,
                            "comment_only": True,
                        },
                    )
                )

        return findings

    def _scan_large_modules(self) -> List[ImprovementFinding]:
        """Report large Python modules with useful structural metrics."""
        findings: List[ImprovementFinding] = []

        for path in self._python_files():
            try:
                source = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError:
                continue

            line_count = len(source.splitlines())
            if line_count < 900:
                continue

            classes = 0
            functions = 0
            imports = 0

            try:
                tree = ast.parse(source, filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes += 1
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions += 1
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        imports += 1
            except SyntaxError:
                pass

            relative = self._relative(path)
            findings.append(
                ImprovementFinding(
                    category="architecture",
                    title="Review oversized Python module",
                    description=(
                        f"{relative} contains {line_count} lines, "
                        f"{classes} classes, {functions} functions and "
                        f"{imports} imports."
                    ),
                    severity="low",
                    file=relative,
                    confidence=0.82,
                    suggested_request=(
                        f"Review {relative} and propose a safe small-module "
                        "refactor. Separate responsibilities without changing "
                        "behaviour, then run tests."
                    ),
                    metadata={
                        "line_count": line_count,
                        "classes": classes,
                        "functions": functions,
                        "imports": imports,
                    },
                )
            )

        return findings

    def _scan_tests(self) -> List[ImprovementFinding]:
        if not self._has_tests():
            return [
                ImprovementFinding(
                    category="tests",
                    title="Add baseline tests",
                    description="No test suite was found.",
                    severity="medium",
                    confidence=0.95,
                    suggested_request=(
                        "Add a focused pytest baseline for Buster startup "
                        "and provider configuration behaviour."
                    ),
                )
            ]

        try:
            compile_result = subprocess.run(
                [
                    "python",
                    "-m",
                    "compileall",
                    "-q",
                    str(self.root / "buster"),
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except Exception as exc:
            return [
                ImprovementFinding(
                    category="tests",
                    title="Compilation health check failed",
                    description=str(exc),
                    severity="medium",
                    confidence=0.9,
                    suggested_request=(
                        "Diagnose why Python compilation could not run, "
                        "make the smallest safe repair, and verify again."
                    ),
                )
            ]

        if compile_result.returncode != 0:
            output = (
                compile_result.stdout[-6000:]
                + "\n"
                + compile_result.stderr[-6000:]
            ).strip()
            return [
                ImprovementFinding(
                    category="tests",
                    title="Repair compilation failure",
                    description=output or "compileall returned a failure.",
                    severity="high",
                    confidence=0.99,
                    suggested_request=(
                        "Diagnose the Python compilation failure, make the "
                        "smallest safe repair, rerun compileall, then run tests."
                    ),
                    metadata={
                        "returncode": compile_result.returncode,
                        "output": output,
                    },
                )
            ]

        try:
            completed = subprocess.run(
                ["python", "-m", "pytest", "-q", "--maxfail=1"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except Exception as exc:
            return [
                ImprovementFinding(
                    category="tests",
                    title="Test health check failed",
                    description=str(exc),
                    severity="medium",
                    confidence=0.9,
                    suggested_request=(
                        "Diagnose why the test health check could not run, "
                        "make the smallest safe repair, and verify again."
                    ),
                )
            ]

        if completed.returncode == 0:
            return []

        output = (
            completed.stdout[-6000:]
            + "\n"
            + completed.stderr[-6000:]
        ).strip()
        return [
            ImprovementFinding(
                category="tests",
                title="Repair failing test suite",
                description=output or "pytest returned a failure.",
                severity="high",
                confidence=0.99,
                suggested_request=(
                    "Diagnose the failing pytest suite, make the smallest "
                    "safe repair, rerun tests, and rollback if tests still fail."
                ),
                metadata={
                    "returncode": completed.returncode,
                    "output": output,
                },
            )
        ]

    def _scan_git(self) -> List[ImprovementFinding]:
        if not (self.root / ".git").exists():
            return [
                ImprovementFinding(
                    category="safety",
                    title="Create Git safety baseline",
                    description="The project is not inside a Git repository.",
                    severity="medium",
                    confidence=0.95,
                    suggested_request=(
                        "Prepare a Git safety baseline without deleting or "
                        "overwriting existing files."
                    ),
                )
            ]

        try:
            completed = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception:
            return []

        counts = {
            "modified": 0,
            "added": 0,
            "deleted": 0,
            "renamed": 0,
            "untracked": 0,
        }

        for raw_line in completed.stdout.splitlines():
            if not raw_line.strip():
                continue

            status = raw_line[:2]

            if status == "??":
                counts["untracked"] += 1
                continue

            if "R" in status:
                counts["renamed"] += 1
            if "A" in status:
                counts["added"] += 1
            if "D" in status:
                counts["deleted"] += 1
            if "M" in status:
                counts["modified"] += 1

        dirty_count = sum(counts.values())
        if dirty_count < 25:
            return []

        return [
            ImprovementFinding(
                category="safety",
                title="Review large uncommitted change set",
                description=(
                    f"Git reports {dirty_count} changed or untracked paths: "
                    f"{counts['modified']} modified, "
                    f"{counts['added']} added, "
                    f"{counts['deleted']} deleted, "
                    f"{counts['renamed']} renamed and "
                    f"{counts['untracked']} untracked."
                ),
                severity="medium",
                confidence=0.95,
                suggested_request=(
                    "Review the Git working tree and create a safe checkpoint "
                    "before self-improvement edits."
                ),
                metadata={
                    "dirty_paths": dirty_count,
                    **counts,
                },
            )
        ]

    def ignore_finding(
        self,
        finding: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Ignore a finding until its source file changes."""
        payload = dict(finding)
        key = self._finding_key(payload)
        relative = str(payload.get("file", ""))
        mtime = self._file_mtime(relative)

        state = self.load_state()
        ignored = state.get("ignored_findings", {})
        if not isinstance(ignored, dict):
            ignored = {}

        ignored[key] = {
            "finding": payload,
            "file": relative,
            "mtime": mtime,
            "ignored_at": utc_now(),
        }
        state["ignored_findings"] = ignored
        self.save_state(state)

        return ignored[key]

    def clear_ignored_findings(self) -> None:
        state = self.load_state()
        state["ignored_findings"] = {}
        self.save_state(state)

    def _filter_ignored(
        self,
        findings: Iterable[ImprovementFinding],
    ) -> List[ImprovementFinding]:
        state = self.load_state()
        ignored = state.get("ignored_findings", {})
        if not isinstance(ignored, dict) or not ignored:
            return list(findings)

        active_ignored = dict(ignored)
        output: List[ImprovementFinding] = []
        changed = False

        for finding in findings:
            payload = finding.to_dict()
            key = self._finding_key(payload)
            record = active_ignored.get(key)

            if not isinstance(record, dict):
                output.append(finding)
                continue

            relative = str(record.get("file", payload.get("file", "")))
            old_mtime = record.get("mtime")
            current_mtime = self._file_mtime(relative)

            if old_mtime == current_mtime:
                continue

            active_ignored.pop(key, None)
            changed = True
            output.append(finding)

        if changed:
            state["ignored_findings"] = active_ignored
            self.save_state(state)

        return output

    def _finding_key(self, finding: Mapping[str, Any]) -> str:
        return "|".join(
            [
                str(finding.get("category", "")),
                str(finding.get("title", "")),
                str(finding.get("file", "")),
                str(finding.get("line", 0)),
            ]
        )

    def _file_mtime(self, relative: str) -> Optional[int]:
        if not relative:
            return None
        path = self.root / relative
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return None

    def _finish(self, result: ImprovementCycleResult) -> ImprovementCycleResult:
        result.finished_at = utc_now()
        state = self.load_state()
        state["last_cycle"] = result.to_dict()
        self.save_state(state)
        history = self._history()
        history.append(result.to_dict())
        self.history_path.write_text(json.dumps(history[-300:], indent=2, default=str), encoding="utf-8")
        self._publish("self_improvement.cycle.finished", result.to_dict())
        return result

    def _publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self.runtime_core is None:
            return
        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        publish = getattr(dispatcher, "publish", None)
        if callable(publish):
            try:
                publish(event_type, payload, source="self_improvement")
            except Exception:
                pass

    def _ensure_files(self) -> None:
        if not self.state_path.exists():
            self.save_state(self.default_state())
        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")

    def _history(self) -> List[Dict[str, Any]]:
        try:
            raw = json.loads(self.history_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except Exception:
            return []

    def _python_files(self) -> Iterable[Path]:
        for path in self.root.rglob("*.py"):
            if any(part in self.excludes for part in path.parts):
                continue
            yield path

    def _relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def _resolve(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    def _has_tests(self) -> bool:
        return (self.root / "tests").exists() or any(self.root.glob("test_*.py")) or any(self.root.glob("*_test.py"))

    def _project_type(self) -> str:
        if (self.root / "build.gradle").exists():
            return "android"
        if any(self.root.rglob("*.ino")):
            return "esp32"
        return "python"

    @staticmethod
    def _deduplicate(findings: Iterable[ImprovementFinding]) -> List[ImprovementFinding]:
        seen = set()
        output: List[ImprovementFinding] = []
        for finding in findings:
            key = (finding.category, finding.title, finding.file, finding.line)
            if key not in seen:
                seen.add(key)
                output.append(finding)
        return output
