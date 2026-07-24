from __future__ import annotations

from .models import AgentRequest


class PromptBuilder:
    """
    Builds prompts for the Python repair agent.

    The model is instructed to return raw Python source only.
    """

    @staticmethod
    def build(
        request: AgentRequest,
        feedback: str = "",
    ) -> str:

        prompt = f"""You are an expert Python Refactoring Specialist.

TARGET FILE:
{request.file_path}

TASK:
{request.instruction}

REQUIREMENTS:

- Return the COMPLETE updated Python file from top to bottom.
- DO NOT truncate, abbreviate, or use placeholders like '# ... rest of code'.
- Ensure every string literal, parenthesis, and block is properly closed and syntactically valid.
- Preserve all unrelated imports.
- Preserve all unrelated classes.
- Preserve all unrelated functions.
- Preserve all unrelated methods.
- Make ONLY the requested changes.
- Return ONLY executable Python source code.
- Do NOT use Markdown.
- Do NOT use code fences.
- Do NOT return a unified diff.
- Do NOT explain your answer.
- Do NOT apologise.
- Do NOT include any conversational text.
- Do NOT omit unchanged code.
- The response must be a complete replacement for the original file.

ORIGINAL SOURCE:

{request.original_code}
"""

        if feedback:
            prompt += f"""

PREVIOUS ATTEMPT FAILED

Reason:
{feedback}

Correct this problem and return the COMPLETE updated Python file.

Remember:

- Return ONLY Python source.
- No truncation or placeholders.
- Ensure valid syntax with no unterminated strings.
- No Markdown.
- No code fences.
- No explanations.
"""

        return prompt