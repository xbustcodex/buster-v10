from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
DT = ROOT / "buster" / "utils" / "datetime_utils.py"

GOOD = """from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_timestamp(timespec: str = "seconds") -> str:
    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat(timespec=timespec)
        .replace("+00:00", "Z")
    )
"""

def main() -> None:
    print("=== Applying v6.5.1 datetime_utils circular import fix ===")
    DT.parent.mkdir(parents=True, exist_ok=True)
    DT.write_text(GOOD, encoding="utf-8")
    print(f"[WRITE] {DT.relative_to(ROOT)}")

    # Safety scan: remove accidental self-import line from datetime_utils if it ever appears again.
    text = DT.read_text(encoding="utf-8")
    text = text.replace("from buster.utils.datetime_utils import utc_now, utc_timestamp\n", "")
    DT.write_text(text, encoding="utf-8")

    print("\nSUCCESS: datetime_utils circular import fixed.")
    print("Next: python -m pytest")
    print('Then: scripts\\test_push.bat "v6.5.1 maintenance modernization"')

if __name__ == "__main__":
    main()
