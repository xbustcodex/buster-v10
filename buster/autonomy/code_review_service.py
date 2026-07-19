from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(slots=True)
class CodeReviewResult:
    success: bool
    summary: str
    evidence: str
    impact: str
    risk: str
    recommended_repair: str
    validation: str
    decision: str
    provider: str = "unknown"
    model: str = "unknown"
    cached: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CodeReviewService:
    """
    Fast local code review.

    Optimisations:
    - reads only 15 lines around a reported location;
    - caps whole-file context when there is no line number;
    - requests compact JSON rather than an essay;
    - caches reviews by finding and file modification time.
    """

    CONTEXT_RADIUS = 15
    MAX_WHOLE_FILE_LINES = 80

    def __init__(
        self,
        root: str | Path,
        ai_manager: Any,
        dispatcher: Any = None,
        cache_path: str | Path = "data/code_review_cache.json",
    ) -> None:
        self.root = Path(root).resolve()
        self.ai_manager = ai_manager
        self.dispatcher = dispatcher
        path = Path(cache_path)
        self.cache_path = (
            path if path.is_absolute() else self.root / path
        )
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def review(
        self,
        finding: Mapping[str, Any],
    ) -> CodeReviewResult:
        payload = dict(finding or {})

        self._publish(
            "self_improvement.review.progress",
            {
                "message": "Reading source...",
                "progress": 10,
            },
        )

        source, mtime = self._source_context(payload)
        cache_key = self._cache_key(payload, mtime)

        self._publish(
            "self_improvement.review.progress",
            {
                "message": "Checking review cache...",
                "progress": 20,
            },
        )

        cached = self._read_cache().get(cache_key)

        if isinstance(cached, dict):
            cached_result = dict(cached)
            cached_result["cached"] = True

            result = CodeReviewResult(**cached_result)

            self._publish(
                "self_improvement.review.progress",
                {
                    "message": "Cached review loaded.",
                    "progress": 100,
                },
            )

            self._publish(
                "self_improvement.review.finished",
                result.to_dict(),
            )

            return result

        provider = str(
            getattr(
                self.ai_manager,
                "current",
                "unknown",
            )
        )
        model = self._current_model()

        self._publish(
            "self_improvement.review.started",
            {
                "title": payload.get("title", ""),
                "provider": provider,
                "model": model,
            },
        )

        self._publish(
            "self_improvement.review.progress",
            {
                "message": "Preparing AI review...",
                "progress": 35,
            },
        )

        prompt = self._prompt(payload, source)

        try:
            self._publish(
                "self_improvement.review.progress",
                {
                    "message": f"Waiting for {provider}...",
                    "progress": 50,
                },
            )

            response = self.ai_manager.complete(
                prompt,
                context=(
                    "Fast read-only code review. "
                    "Return JSON only. "
                    "Do not claim that files were changed."
                ),
            )

            self._publish(
                "self_improvement.review.progress",
                {
                    "message": "Formatting AI results...",
                    "progress": 80,
                },
            )

            parsed = self._parse_json(
                 str(response or "")
            )

            result = CodeReviewResult(
                success=True,
                summary=self._short(
                    parsed.get("summary")
                ),
                evidence=self._short(
                     parsed.get("evidence")
                ),
                impact=self._short(
                    parsed.get("impact")
                ),
                risk=self._risk(
                    parsed.get("risk")
                ),
                recommended_repair=self._short(
                    parsed.get("recommended_repair")
                ),
                validation=self._short(
                    parsed.get("validation")
                ),
                decision=self._decision(
                    parsed.get("decision")
                ),
                provider=provider,
                model=model,
                cached=False,
            )

        except Exception as exc:
            self._publish(
                "self_improvement.review.progress",
                {
                    "message": "AI review failed. Building safe fallback...",
                    "progress": 85,
                },
            )

            result = self._fallback(
                payload,
                provider,
                model,
                str(exc),
            )

        self._publish(
            "self_improvement.review.progress",
            {
                "message": "Saving review...",
                "progress": 95,
            },
        )

        cache = self._read_cache()
        cache[cache_key] = result.to_dict()
        cache[cache_key]["cached"] = False

        try:
            self.cache_path.write_text(
                json.dumps(
                    cache,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            self._publish(
                "self_improvement.review.cache_failed",
                {
                    "error": str(exc),
                    "cache_path": str(self.cache_path),
                },
            )

        self._publish(
            "self_improvement.review.progress",
            {
                "message": "Review complete.",
                "progress": 100,
            },
        )

        self._publish(
            "self_improvement.review.finished",
            result.to_dict(),
        )

        return result

    def _prompt(
        self,
        finding: Mapping[str, Any],
        source: str,
    ) -> str:
        return f"""
Review this scanner finding.

Title: {finding.get("title", "")}
Category: {finding.get("category", "")}
Severity: {finding.get("severity", "")}
Description: {finding.get("description", "")}
Suggested action: {finding.get("suggested_request", "")}

Relevant source:
{source or "No source context available."}

Return one compact JSON object only:
{{
  "summary": "maximum 2 sentences",
  "evidence": "maximum 2 sentences",
  "impact": "maximum 2 sentences",
  "risk": "LOW|MEDIUM|HIGH|CRITICAL",
  "recommended_repair": "maximum 3 short sentences",
  "validation": "maximum 2 short sentences",
  "decision": "FIX NOW|PLAN FIRST|MONITOR|IGNORE"
}}

Rules:
- Use only visible evidence.
- Do not invent defects.
- A large file is not automatically broken.
- Do not recommend a fix unrelated to the finding.
- Keep the whole response under 180 words.
""".strip()

    def _source_context(
        self,
        finding: Mapping[str, Any],
    ) -> tuple[str, int]:
        relative = str(finding.get("file", "") or "").strip()
        if not relative:
            return "", 0

        path = (self.root / relative).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            return "", 0

        if not path.is_file():
            return "", 0

        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
        line = self._safe_int(finding.get("line", 0))

        if line > 0:
            start = max(1, line - self.CONTEXT_RADIUS)
            end = min(len(lines), line + self.CONTEXT_RADIUS)
        else:
            start = 1
            end = min(len(lines), self.MAX_WHOLE_FILE_LINES)

        body = "\n".join(
            f"{index:>5}: {lines[index - 1]}"
            for index in range(start, end + 1)
        )
        return body, path.stat().st_mtime_ns

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < start:
            raise ValueError("AI response did not contain JSON.")
        value = json.loads(cleaned[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("AI review JSON was not an object.")
        return value

    def _fallback(
        self,
        finding: Mapping[str, Any],
        provider: str,
        model: str,
        error: str,
    ) -> CodeReviewResult:
        severity = self._risk(finding.get("severity"))
        decision = {
            "CRITICAL": "FIX NOW",
            "HIGH": "FIX NOW",
            "MEDIUM": "PLAN FIRST",
            "LOW": "MONITOR",
        }.get(severity, "MONITOR")

        return CodeReviewResult(
            success=False,
            summary=str(
                finding.get(
                    "description",
                    "The scanner reported a project finding.",
                )
            ),
            evidence="AI analysis was unavailable; this is the scanner result.",
            impact="Review the affected code before making changes.",
            risk=severity,
            recommended_repair=str(
                finding.get(
                    "suggested_request",
                    "Prepare a focused repair plan.",
                )
            ),
            validation="Run compileall, focused tests, then the full test suite.",
            decision=decision,
            provider=provider,
            model=model,
            error=error,
        )

    def _cache_key(
        self,
        finding: Mapping[str, Any],
        mtime: int,
    ) -> str:
        raw = json.dumps(
            {
                "finding": dict(finding),
                "mtime": mtime,
                "model": self._current_model(),
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def _read_cache(self) -> dict[str, Any]:
        try:
            data = json.loads(
                self.cache_path.read_text(encoding="utf-8")
            )
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _current_model(self) -> str:
        method = getattr(self.ai_manager, "current_model", None)
        if callable(method):
            try:
                return str(method() or "unknown")
            except Exception:
                pass

        provider = getattr(
            self.ai_manager,
            "providers",
            {},
        ).get(
            getattr(self.ai_manager, "current", "")
        )
        return str(
            getattr(provider, "model", "unknown") or "unknown"
        )

    def _publish(
        self,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        publish = getattr(self.dispatcher, "publish", None)
        if callable(publish):
            try:
                publish(
                    event_type,
                    dict(payload),
                    source="code_review",
                )
            except Exception:
                pass

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _short(value: Any) -> str:
        return str(value or "—").strip()

    @staticmethod
    def _risk(value: Any) -> str:
        risk = str(value or "LOW").upper().strip()
        return (
            risk
            if risk in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            else "LOW"
        )

    @staticmethod
    def _decision(value: Any) -> str:
        decision = str(value or "MONITOR").upper().strip()
        return (
            decision
            if decision
            in {"FIX NOW", "PLAN FIRST", "MONITOR", "IGNORE"}
            else "MONITOR"
        )
