from pathlib import Path

ROOT = Path(__file__).parent

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote:", path)

write(ROOT / "buster_knowledge.py", r'''
from __future__ import annotations

import sys
from pathlib import Path

from buster.knowledge.knowledge_engine import RepositoryKnowledgeEngine


HELP = """
Buster Knowledge Engine CLI v3.4.1

Usage:
  python buster_knowledge.py "summarize file buster\\vision\\engine.py"
  python buster_knowledge.py "what depends on openrouter"
  python buster_knowledge.py "rename impact start"
  python buster_knowledge.py "Which classes inherit Agent?"
  python buster_knowledge.py "todo"
  python buster_knowledge.py "vision"

Examples:
  python buster_knowledge.py "summarize file buster\\brain\\engine.py"
  python buster_knowledge.py "what depends on cv2"
  python buster_knowledge.py "who calls start"
"""


def main():
    root = Path(__file__).parent

    if len(sys.argv) <= 1:
        print(HELP)
        return

    question = " ".join(sys.argv[1:]).strip()

    if question.lower() in {"help", "-h", "--help", "/?"}:
        print(HELP)
        return

    print("=== Buster Knowledge Engine v3.4.1 ===")
    print("Question:", question)
    print()

    engine = RepositoryKnowledgeEngine(root)
    answer = engine.ask(question)

    print(answer)


if __name__ == "__main__":
    main()
''')

write(ROOT / "test_v3_4_1_knowledge_engine_cli.py", r'''
import subprocess
import sys
from pathlib import Path


def run(question: str):
    root = Path(__file__).parent
    cmd = [sys.executable, str(root / "buster_knowledge.py"), question]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=root)

    print("=" * 60)
    print("QUESTION:", question)
    print("-" * 60)
    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise SystemExit(result.returncode)

    return result.stdout


def main():
    out1 = run("summarize file buster\\vision\\engine.py")
    out2 = run("what depends on openrouter")
    out3 = run("rename impact start")
    out4 = run("Which classes inherit Agent?")

    assert "File summary" in out1
    assert "Dependencies for openrouter" in out2
    assert "Rename impact" in out3
    assert "BuilderAgent" in out4

    print()
    print("SUCCESS: v3.4.1 Knowledge Engine CLI installed.")


if __name__ == "__main__":
    main()
''')

write(ROOT / "scripts" / "knowledge.bat", r'''
@echo off
cd /d "%~dp0\.."
python buster_knowledge.py %*
''')

print()
print("Buster v3.4.1 Knowledge Engine CLI patch complete.")
print("Run:")
print("python test_v3_4_1_knowledge_engine_cli.py")
print()
print("Then try:")
print('python buster_knowledge.py "summarize file buster\\vision\\engine.py"')