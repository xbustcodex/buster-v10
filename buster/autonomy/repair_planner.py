from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(slots=True)
class RepairPlan:
    """Structured, read-only implementation plan for one scanner finding."""

    success: bool
    title: str
    goal: str
    risk: str
    estimated_files: int
    estimated_effort: str
    steps: list[str]
    warnings: list[str]
    decision: str
    provider: str
    model: str
    cached: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RepairPlanner:
    """Create a compact, read-only repair plan from a finding and review."""

    CACHE_VERSION = 1
    MAX_TEXT_LENGTH = 700
    MAX_STEPS = 10
    MAX_WARNINGS = 6

    VALID_RISKS = {"low", "medium", "high", "critical"}
    VALID_DECISIONS = {
        "recommended",
        "optional",
        "investigate",
        "defer",
        "not_recommended",
    }

    def __init__(
        self,
        root: str | Path,
        ai_manager: Any,
        dispatcher: Any | None = None,
        cache_path: str | Path | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.ai_manager = ai_manager
        self.dispatcher = dispatcher

        if cache_path is None:
            cache_path = (
                self.root
                / "data"
                / "self_improvement"
                / "repair_plan_cache.json"
            )

        self.cache_path = Path(cache_path).expanduser()
        if not self.cache_path.is_absolute():
            self.cache_path = self.root / self.cache_path

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def plan(
        self,
        finding: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> RepairPlan:
        finding_payload = dict(finding or {})
        review_payload = dict(review or {})

        self._publish(
            "self_improvement.plan.progress",
            {"message": "Preparing repair plan...", "progress": 10},
        )

        cache_key = self._cache_key(finding_payload, review_payload)

        self._publish(
            "self_improvement.plan.progress",
            {"message": "Checking repair plan cache...", "progress": 20},
        )

        cached = self._read_cache().get(cache_key)
        if isinstance(cached, dict):
            cached_payload = dict(cached)
            cached_payload["cached"] = True
            try:
                result = RepairPlan(**cached_payload)
            except TypeError:
                result = self._normalise_result(
                    cached_payload,
                    provider=str(cached_payload.get("provider", "unknown")),
                    model=str(cached_payload.get("model", "unknown")),
                )
                result.cached = True

            self._publish(
                "self_improvement.plan.progress",
                {"message": "Cached repair plan loaded.", "progress": 100},
            )
            self._publish("self_improvement.plan.finished", result.to_dict())
            return result

        provider = str(getattr(self.ai_manager, "current", "unknown"))
        model = self._current_model()

        self._publish(
            "self_improvement.plan.started",
            {
                "title": finding_payload.get("title", ""),
                "provider": provider,
                "model": model,
            },
        )

        try:
            self._publish(
                "self_improvement.plan.progress",
                {"message": "Building planning prompt...", "progress": 35},
            )

            prompt = self._prompt(finding_payload, review_payload)

            self._publish(
                "self_improvement.plan.progress",
                {"message": f"Waiting for {provider}...", "progress": 50},
            )

            response = self.ai_manager.complete(
                prompt,
                context=(
                    "Create a concise, read-only software repair plan. "
                    "Return valid JSON only. Do not generate a patch, "
                    "do not claim that files were changed, and do not "
                    "invent project details that are not present."
                ),
            )

            self._publish(
                "self_improvement.plan.progress",
                {"message": "Formatting repair plan...", "progress": 80},
            )

            parsed = self._parse_json(str(response or ""))
            result = self._normalise_result(
                parsed,
                provider=provider,
                model=model,
            )
        except Exception as exc:
            self._publish(
                "self_improvement.plan.progress",
                {
                    "message": (
                        "AI planning failed. Building a safe fallback plan..."
                    ),
                    "progress": 85,
                },
            )
            result = self._fallback(
                finding_payload,
                review_payload,
                provider,
                model,
                str(exc),
            )

        self._publish(
            "self_improvement.plan.progress",
            {"message": "Saving repair plan...", "progress": 95},
        )
        self._write_cache(cache_key, result)

        self._publish(
            "self_improvement.plan.progress",
            {"message": "Repair plan complete.", "progress": 100},
        )
        self._publish("self_improvement.plan.finished", result.to_dict())
        return result

    def _prompt(
        self,
        finding: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> str:
        finding_json = json.dumps(
            self._serialisable(finding),
            indent=2,
            ensure_ascii=False,
        )
        review_json = json.dumps(
            self._serialisable(review),
            indent=2,
            ensure_ascii=False,
        )

        return f"""
You are the repair planner inside Buster Desktop AI OS.

Create a small, practical implementation plan for the selected code finding.
The plan will be reviewed by a human before any code generation occurs.

Rules:
- Return one JSON object only.
- Do not include Markdown fences.
- Do not generate code or a unified diff.
- Do not claim that any file was changed.
- Use only evidence contained in the finding and review.
- Keep the public API stable unless the evidence explicitly requires a change.
- Prefer small modules and focused classes.
- Include concrete verification steps.
- Use at most {self.MAX_STEPS} plan steps.
- Use at most {self.MAX_WARNINGS} warnings.
- estimated_files must be an integer.
- risk must be one of: low, medium, high, critical.
- decision must be one of: recommended, optional, investigate, defer, not_recommended.

Required JSON schema:
{{
  "success": true,
  "title": "Short repair plan title",
  "goal": "One concise sentence describing the outcome",
  "risk": "low",
  "estimated_files": 1,
  "estimated_effort": "10-20 minutes",
  "steps": [
    "Inspect the affected module and identify the exact boundary",
    "Make the smallest focused change",
    "Update imports or tests if required",
    "Compile and run relevant tests"
  ],
  "warnings": [
    "Preserve the existing public API"
  ],
  "decision": "recommended"
}}

Scanner finding:
{finding_json}

AI code review:
{review_json}
""".strip()

    def _normalise_result(
        self,
        payload: Mapping[str, Any],
        provider: str,
        model: str,
    ) -> RepairPlan:
        steps = self._string_list(payload.get("steps"), self.MAX_STEPS)
        warnings = self._string_list(payload.get("warnings"), self.MAX_WARNINGS)

        if not steps:
            steps = [
                "Inspect the affected source and confirm the finding.",
                "Implement the smallest focused repair.",
                "Compile the affected module.",
                "Run the relevant tests and rescan the project.",
            ]

        return RepairPlan(
            success=bool(payload.get("success", True)),
            title=self._short(
                payload.get("title"),
                default="Repair selected finding",
            ),
            goal=self._short(
                payload.get("goal"),
                default="Resolve the selected finding with the smallest safe change.",
            ),
            risk=self._risk(payload.get("risk")),
            estimated_files=self._positive_int(
                payload.get("estimated_files"),
                default=1,
            ),
            estimated_effort=self._short(
                payload.get("estimated_effort"),
                default="Estimate unavailable",
            ),
            steps=steps,
            warnings=warnings,
            decision=self._decision(payload.get("decision")),
            provider=provider,
            model=model,
            cached=False,
            error=self._short(payload.get("error"), default=""),
        )

    def _fallback(
        self,
        finding: Mapping[str, Any],
        review: Mapping[str, Any],
        provider: str,
        model: str,
        error: str,
    ) -> RepairPlan:
        return RepairPlan(
            success=False,
            title=self._short(
                finding.get("title"),
                default="Repair selected finding",
            ),
            goal=self._short(
                review.get("summary"),
                default=self._short(
                    finding.get("description"),
                    default=(
                        "Resolve the scanner finding using a minimal, "
                        "reviewable change."
                    ),
                ),
            ),
            risk=self._risk(
                review.get("risk", finding.get("severity", "medium"))
            ),
            estimated_files=1,
            estimated_effort="Estimate unavailable",
            steps=[
                "Inspect the exact source location referenced by the finding.",
                self._short(
                    review.get("recommended_repair"),
                    default="Implement the smallest focused correction.",
                ),
                "Preserve existing imports, signals, and public interfaces.",
                self._short(
                    review.get("validation"),
                    default=(
                        "Compile the affected module, run relevant tests, "
                        "and repeat the self-improvement scan."
                    ),
                ),
            ],
            warnings=[
                (
                    "The AI provider did not return a valid structured plan; "
                    "review this fallback carefully before continuing."
                )
            ],
            decision="investigate",
            provider=provider,
            model=model,
            cached=False,
            error=self._short(error, default="Unknown planner error"),
        )

    def _cache_key(
        self,
        finding: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> str:
        payload = {
            "version": self.CACHE_VERSION,
            "finding": self._serialisable(finding),
            "review": self._serialisable(review),
            "provider": str(getattr(self.ai_manager, "current", "unknown")),
            "model": self._current_model(),
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _read_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_cache(self, cache_key: str, result: RepairPlan) -> None:
        cache = self._read_cache()
        cached_result = result.to_dict()
        cached_result["cached"] = False
        cache[cache_key] = cached_result

        try:
            self.cache_path.write_text(
                json.dumps(cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            self._publish(
                "self_improvement.plan.cache_failed",
                {
                    "error": str(exc),
                    "cache_path": str(self.cache_path),
                },
            )

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = str(text or "").strip()
        if not cleaned:
            raise ValueError("The AI planner returned an empty response.")

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("The AI planner did not return a JSON object.")
            payload = json.loads(cleaned[start : end + 1])

        if not isinstance(payload, dict):
            raise ValueError("The AI planner response was not a JSON object.")
        return payload

    def _current_model(self) -> str:
        candidates = (
            "current_model",
            "model",
            "active_model",
            "ollama_model",
        )
        for name in candidates:
            value = getattr(self.ai_manager, name, None)
            if value:
                return str(value)

        config = getattr(self.ai_manager, "config", None)
        if isinstance(config, Mapping):
            for name in candidates:
                value = config.get(name)
                if value:
                    return str(value)
        return "unknown"

    def _publish(
        self,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        if self.dispatcher is None:
            return

        data = dict(payload or {})
        try:
            publish = getattr(self.dispatcher, "publish", None)
            if callable(publish):
                publish(event_type, data)
                return

            emit = getattr(self.dispatcher, "emit", None)
            if callable(emit):
                emit(event_type, data)
        except Exception:
            return

    def _risk(self, value: Any) -> str:
        text = str(value or "medium").strip().lower()
        aliases = {
            "info": "low",
            "minor": "low",
            "moderate": "medium",
            "warning": "medium",
            "major": "high",
            "severe": "high",
            "blocker": "critical",
        }
        text = aliases.get(text, text)
        return text if text in self.VALID_RISKS else "medium"

    def _decision(self, value: Any) -> str:
        text = str(value or "investigate").strip().lower()
        text = text.replace(" ", "_").replace("-", "_")
        aliases = {
            "recommend": "recommended",
            "proceed": "recommended",
            "approve": "recommended",
            "review": "investigate",
            "needs_review": "investigate",
            "skip": "defer",
            "reject": "not_recommended",
        }
        text = aliases.get(text, text)
        return text if text in self.VALID_DECISIONS else "investigate"

    def _short(self, value: Any, default: str = "") -> str:
        text = str(value if value is not None else default).strip()
        text = re.sub(r"\s+", " ", text)
        if len(text) > self.MAX_TEXT_LENGTH:
            text = text[: self.MAX_TEXT_LENGTH - 1].rstrip() + "…"
        return text

    def _string_list(self, value: Any, limit: int) -> list[str]:
        if isinstance(value, str):
            raw_items: Sequence[Any] = [
                line for line in value.splitlines() if line.strip()
            ]
        elif isinstance(value, Sequence):
            raw_items = value
        else:
            return []

        output: list[str] = []
        for item in raw_items:
            text = self._short(item)
            text = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", text)
            if not text or text in output:
                continue
            output.append(text)
            if len(output) >= limit:
                break
        return output

    @staticmethod
    def _positive_int(value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(parsed, 100))

    def _serialisable(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): self._serialisable(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [self._serialisable(item) for item in value]
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        if hasattr(value, "to_dict"):
            try:
                return self._serialisable(value.to_dict())
            except Exception:
                pass
        return str(value)
