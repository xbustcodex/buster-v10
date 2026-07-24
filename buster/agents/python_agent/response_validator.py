from __future__ import annotations

import re


class ResponseValidator:
    """Validates and extracts clean Python code from AI provider outputs."""

    @staticmethod
    def extract_code(raw_response: str) -> str:
        if not raw_response:
            return ""

        text = str(raw_response).strip()

        # unwrap markdown if present
        if text.startswith("```"):
            first = text.find("\n")
            if first != -1:
                text = text[first + 1:]

            if text.endswith("```"):
                text = text[:-3]

        return text.strip()

    @staticmethod
    def is_conversational(text: str) -> bool:
        if not text:
            return True

        lower = text.lower()
        triggers = ["i cannot", "here is", "sure,", "as an ai", "sorry"]
        
        first_line = text.splitlines()[0].lower() if text.splitlines() else ""
        if any(t in first_line for t in triggers) and not any(k in lower for k in ["def ", "import "]):
            return True

        return False