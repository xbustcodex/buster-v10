from __future__ import annotations

import logging
from typing import Any, Optional

from .compiler import CodeCompiler
from .diff_builder import DiffBuilder
from .models import AgentRequest, PreviewDiff, QualityMetrics
from .prompt_builder import PromptBuilder
from .quality_score import QualityScorer
from .response_validator import ResponseValidator
from .retry_policy import RetryPolicy
from .syntax_checker import SyntaxChecker

logger = logging.getLogger("PythonAgentWorker")


class PythonAgentWorker:
    """
    Generates, validates, scores, and previews AI-produced Python changes.

    The worker never writes directly to the target file. It returns a
    PreviewDiff that can be reviewed and passed to the patch-application
    pipeline.
    """

    def __init__(
        self,
        provider: Any,
        event_bus: Any = None,
        max_retries: int = 4,
        score_threshold: float = 50.0,
    ) -> None:
        if provider is None:
            raise ValueError("PythonAgentWorker requires an AI provider.")

        self.provider = provider
        self.event_bus = event_bus
        self.retry_policy = RetryPolicy(max_retries=max_retries)
        self.score_threshold = float(score_threshold)

    def emit_event(
        self,
        event_type: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Publish a lifecycle event to Buster's Event Bus and log."""
        payload = dict(data or {})
        full_event_type = f"python_agent.{event_type}"

        logger.info("[%s] %s", full_event_type, payload)

        publish = getattr(self.event_bus, "publish", None)
        if not callable(publish):
            return

        try:
            publish(full_event_type, payload, source="python_agent")
        except TypeError:
            try:
                publish(full_event_type, payload)
            except Exception:
                logger.exception(
                    "Failed to publish event: %s",
                    full_event_type,
                )
        except Exception:
            logger.exception(
                "Failed to publish event: %s",
                full_event_type,
            )

    def run(self, request: AgentRequest) -> PreviewDiff:
        """Run the Python repair workflow and return a reviewable preview."""
        self.emit_event(
            "started",
            {"file": request.file_path},
        )

        feedback = ""
        last_error = ""
        self.retry_policy.reset()

        while self.retry_policy.can_retry():
            self.retry_policy.increment()
            attempt = self.retry_policy.attempt

            try:
                self.emit_event(
                    "prompt_created",
                    {"attempt": attempt},
                )

                prompt = PromptBuilder.build(
                    request,
                    feedback=feedback,
                )

                self.emit_event(
                    "request_sent",
                    {"attempt": attempt},
                )

                raw_response = self._call_provider(prompt)
                print("\n================ RAW RESPONSE TYPE ================")
                print(type(raw_response))

                print("\n================ RAW RESPONSE ================")
                print(repr(raw_response[:1000] if isinstance(raw_response, str) else raw_response))

                print("\n================ CLEANED RESPONSE ================")
                cleaned_code = ResponseValidator.extract_code(raw_response)

                print(cleaned_code[:1000])
                print("--------------------------------")
                print("LINES:", len(cleaned_code.splitlines()))
                print("CHARS:", len(cleaned_code))

                self.emit_event(
                    "response_received",
                    {"attempt": attempt},
                )

                cleaned_code = ResponseValidator.extract_code(raw_response)
                
                if not cleaned_code.strip():
                    last_error = "Provider returned an empty response."
                    self.emit_event(
                        "retry",
                        {
                            "reason": "empty_response",
                            "attempt": attempt,
                        },
                    )
                    continue

                if ResponseValidator.is_conversational(cleaned_code):
                    last_error = "The provider returned conversational or refusal text."
                    feedback = (
                        "The previous response was not valid replacement "
                        "Python source code. Return the complete updated "
                        "Python file only, with no explanation or refusal."
                    )
                    self.emit_event(
                        "retry",
                        {
                            "reason": "invalid_response",
                            "error": last_error,
                            "attempt": attempt,
                        },
                    )
                    continue

                syntax_ok, syntax_error = SyntaxChecker.check(cleaned_code)
                if not syntax_ok:
                    last_error = str(syntax_error)
                    feedback = (
                        "The previous generated file had a Python syntax "
                        f"error: {syntax_error}. Correct the syntax while "
                        "preserving the requested change and all existing "
                        "classes and functions."
                    )
                    self.emit_event(
                        "retry",
                        {
                            "reason": "syntax_error",
                            "error": str(syntax_error),
                            "attempt": attempt,
                        },
                    )
                    continue

                self.emit_event(
                    "syntax_ok",
                    {"attempt": attempt},
                )

                compile_ok, compile_error = CodeCompiler.check(cleaned_code)
                if not compile_ok:
                    last_error = str(compile_error)
                    feedback = (
                        "The previous generated file failed compilation: "
                        f"{compile_error}. Return a complete corrected "
                        "Python file."
                    )
                    self.emit_event(
                        "retry",
                        {
                            "reason": "compile_error",
                            "error": str(compile_error),
                            "attempt": attempt,
                        },
                    )
                    continue

                self.emit_event(
                    "compile_ok",
                    {"attempt": attempt},
                )

                quality = QualityScorer.evaluate(
                    request.original_code,
                    cleaned_code,
                    syntax_ok,
                    compile_ok,
                )

                if not quality.is_acceptable(self.score_threshold):
                    last_error = (
                        f"Quality score too low: {quality.overall_score:.1f}%"
                    )
                    feedback = (
                        "The previous replacement removed or changed too "
                        "much existing code. Preserve all required imports, "
                        "classes, methods, functions, and behavior unless "
                        "the instruction explicitly requires changing them. "
                        f"Previous score: {quality.overall_score:.1f}%."
                    )
                    self.emit_event(
                        "retry",
                        {
                            "reason": "low_quality",
                            "score": quality.overall_score,
                            "attempt": attempt,
                        },
                    )
                    continue

                diff_text = DiffBuilder.build_unified_diff(
                    request.file_path,
                    request.original_code,
                    cleaned_code,
                )

                if not str(diff_text or "").strip():
                    last_error = "The generated code produced an empty diff."
                    feedback = (
                        "The previous response made no effective change. "
                        "Apply the requested repair and return the complete "
                        "updated Python file."
                    )
                    self.emit_event(
                        "retry",
                        {
                            "reason": "empty_diff",
                            "attempt": attempt,
                        },
                    )
                    continue

                self.emit_event(
                    "preview_ready",
                    {
                        "score": quality.overall_score,
                        "attempt": attempt,
                    },
                )

                return PreviewDiff(
                    file_path=request.file_path,
                    original_code=request.original_code,
                    proposed_code=cleaned_code,
                    diff_text=diff_text,
                    quality=quality,
                    success=True,
                    error_message="",
                )

            except Exception as exc:
                last_error = str(exc)
                feedback = (
                    "The previous attempt failed internally with this "
                    f"error: {exc}. Return the complete valid updated "
                    "Python file only."
                )
                logger.exception(
                    "Python agent attempt %s failed",
                    attempt,
                )
                self.emit_event(
                    "retry",
                    {
                        "reason": "worker_error",
                        "error": str(exc),
                        "attempt": attempt,
                    },
                )

        self.emit_event(
            "failed",
            {
                "attempts": self.retry_policy.attempt,
                "error": last_error,
            },
        )

        return PreviewDiff(
            file_path=request.file_path,
            original_code=request.original_code,
            proposed_code="",
            diff_text="",
            quality=QualityMetrics(),
            success=False,
            error_message=(
                "Failed to generate valid Python code after "
                f"{self.retry_policy.max_retries} attempts."
                + (
                    f" Last error: {last_error}"
                    if last_error
                    else ""
                )
            ),
        )

    def _call_provider(self, prompt: str) -> str:
        """
        Call a compatible AI provider.

        Supported methods:
            generate(prompt)
            complete(prompt)
            run(prompt)
            callable(prompt)
        """
        if callable(self.provider):
            response = self.provider(prompt)
            return self._response_to_text(response)

        for method_name in (
            "generate",
            "complete",
            "run",
        ):
            method = getattr(
                self.provider,
                method_name,
                None,
            )
            if callable(method):
                response = method(prompt)
                return self._response_to_text(response)

        raise RuntimeError(
            "The configured provider exposes no supported generation method."
        )

    @staticmethod
    def extract_code(response: str) -> str:
        """
        Extract Python source from an AI response.

        Preferred format:
            raw Python source

        Also supports:
            ```python
            ...
            ```
        """

        text = str(response or "").strip()

        if not text:
            return ""

        lower = text.lower()

        if "```python" in lower:
            start = lower.find("```python") + len("```python")
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # Preferred path: raw Python
        return text


    @staticmethod
    def _response_to_text(response: Any) -> str:
        if response is None:
            return ""

        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            for key in (
                "content",
                "text",
                "response",
                "output",
                "message",
            ):
                value = response.get(key)
                if isinstance(value, str):
                    return value

        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content

        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text

        return str(response)


__all__ = ["PythonAgentWorker"]