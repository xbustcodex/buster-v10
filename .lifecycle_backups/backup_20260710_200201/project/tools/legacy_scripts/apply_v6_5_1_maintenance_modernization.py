from __future__ import annotations

from pathlib import Path
import re
import json
import shutil

ROOT = Path(__file__).resolve().parent


DATETIME_UTILS = '\nfrom __future__ import annotations\n\nfrom datetime import UTC, datetime\n\n\ndef utc_now() -> datetime:\n    """Return timezone-aware current UTC datetime."""\n    return datetime.now(UTC)\n\n\ndef utc_timestamp(timespec: str = "seconds") -> str:\n    """Return ISO UTC timestamp ending in Z."""\n    return (\n        datetime.now(UTC)\n        .replace(microsecond=0 if timespec == "seconds" else datetime.now(UTC).microsecond)\n        .isoformat(timespec=timespec)\n        .replace("+00:00", "Z")\n    )\n'

JSON_UTILS = '\nfrom __future__ import annotations\n\nfrom pathlib import Path\nfrom typing import Any\nimport json\nimport os\nimport tempfile\n\n\ndef load_json(path: str | Path, default: Any = None) -> Any:\n    target = Path(path)\n    if not target.exists():\n        return default\n    try:\n        return json.loads(target.read_text(encoding="utf-8"))\n    except Exception:\n        return default\n\n\ndef save_json(path: str | Path, data: Any, indent: int = 2) -> None:\n    target = Path(path)\n    target.parent.mkdir(parents=True, exist_ok=True)\n\n    fd, tmp_name = tempfile.mkstemp(\n        prefix=target.name + ".",\n        suffix=".tmp",\n        dir=str(target.parent),\n        text=True,\n    )\n\n    try:\n        with os.fdopen(fd, "w", encoding="utf-8") as handle:\n            json.dump(data, handle, indent=indent, ensure_ascii=False)\n            handle.write("\\n")\n        Path(tmp_name).replace(target)\n    finally:\n        tmp = Path(tmp_name)\n        if tmp.exists():\n            tmp.unlink(missing_ok=True)\n'

LOGGER_UTILS = '\nfrom __future__ import annotations\n\nfrom pathlib import Path\nfrom typing import Any\nimport logging\n\n\ndef get_logger(name: str = "buster") -> logging.Logger:\n    logger = logging.getLogger(name)\n    if logger.handlers:\n        return logger\n\n    logger.setLevel(logging.INFO)\n    Path("logs").mkdir(parents=True, exist_ok=True)\n\n    formatter = logging.Formatter(\n        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"\n    )\n\n    file_handler = logging.FileHandler("logs/buster.log", encoding="utf-8")\n    file_handler.setFormatter(formatter)\n\n    stream_handler = logging.StreamHandler()\n    stream_handler.setFormatter(formatter)\n\n    logger.addHandler(file_handler)\n    logger.addHandler(stream_handler)\n    return logger\n\n\ndef log_event(name: str, message: str, **data: Any) -> None:\n    logger = get_logger(name)\n    if data:\n        logger.info("%s | %s", message, data)\n    else:\n        logger.info(message)\n'

UTILS_INIT = '\nfrom .datetime_utils import utc_now, utc_timestamp\nfrom .json_utils import load_json, save_json\nfrom .logger import get_logger, log_event\n\n__all__ = [\n    "utc_now",\n    "utc_timestamp",\n    "load_json",\n    "save_json",\n    "get_logger",\n    "log_event",\n]\n'

TEST_CODE = '\nimport warnings\nfrom pathlib import Path\n\nfrom buster.utils import utc_timestamp, load_json, save_json, get_logger\n\n\ndef test_utils_datetime_json_logger(tmp_path):\n    stamp = utc_timestamp()\n    assert stamp.endswith("Z")\n    assert "+00:00" not in stamp\n\n    path = tmp_path / "nested" / "data.json"\n    save_json(path, {"ok": True})\n    assert load_json(path)["ok"] is True\n\n    logger = get_logger("buster.test")\n    assert logger.name == "buster.test"\n\n\ndef test_no_datetime_utcnow_usage_in_buster_source():\n    root = Path("buster")\n    offenders = []\n    for path in root.rglob("*.py"):\n        text = path.read_text(encoding="utf-8", errors="ignore")\n        if "datetime.utcnow(" in text:\n            offenders.append(str(path))\n    assert not offenders, "datetime.utcnow() still used in: " + ", ".join(offenders)\n'

PYTEST_INI = '\n[pytest]\nfilterwarnings =\n    error::DeprecationWarning\n'


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"[WRITE] {path.relative_to(ROOT)}")


def patch_utcnow_usage() -> list[str]:
    changed = []

    for path in (ROOT / "buster").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        original = text

        # Simple direct pattern used by older Buster modules:
        # datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        text = text.replace(
            'datetime.utcnow().replace(microsecond=0).isoformat() + "Z"',
            'utc_timestamp()',
        )
        text = text.replace(
            "datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'",
            "utc_timestamp()",
        )

        # Other direct utcnow calls.
        text = text.replace("datetime.utcnow()", "utc_now().replace(tzinfo=None)")

        # If we inserted utc_timestamp/utc_now, ensure import exists.
        if ("utc_timestamp()" in text or "utc_now()" in text) and "buster.utils.datetime_utils" not in text:
            lines = text.splitlines()
            insert_at = 0
            # Keep future imports first.
            for i, line in enumerate(lines):
                if line.startswith("from __future__ import"):
                    insert_at = i + 1

            # Avoid placing between import block awkwardly; direct safe insertion after future imports.
            lines.insert(insert_at, "from buster.utils.datetime_utils import utc_now, utc_timestamp")
            text = "\n".join(lines) + "\n"

        if text != original:
            backup = path.with_suffix(path.suffix + ".bak_v651")
            if not backup.exists():
                backup.write_text(original, encoding="utf-8")
            path.write_text(text, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
            print(f"[PATCH] {path.relative_to(ROOT)}")

    return changed


def patch_autonomy_records_directly() -> None:
    path = ROOT / "buster" / "autonomy" / "records.py"
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8", errors="ignore")
    if "datetime.utcnow()" not in text:
        return

    backup = path.with_suffix(path.suffix + ".bak_v651")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = text.replace("from datetime import datetime", "from datetime import datetime\nfrom buster.utils.datetime_utils import utc_timestamp")
    text = text.replace('datetime.utcnow().replace(microsecond=0).isoformat() + "Z"', "utc_timestamp()")
    text = text.replace("datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'", "utc_timestamp()")
    text = text.replace("datetime.utcnow()", "datetime.fromisoformat(utc_timestamp().replace('Z', '+00:00'))")
    path.write_text(text, encoding="utf-8")
    print(f"[PATCH] {path.relative_to(ROOT)}")


def ensure_pytest_ini() -> None:
    path = ROOT / "pytest.ini"
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "error::DeprecationWarning" in text:
            print("[SKIP] pytest.ini already treats DeprecationWarning as error")
            return
        backup = path.with_suffix(".ini.bak_v651")
        if not backup.exists():
            backup.write_text(text, encoding="utf-8")
        if "filterwarnings" not in text:
            text += "\nfilterwarnings =\n    error::DeprecationWarning\n"
        else:
            text += "\n# v6.5.1 strict warning policy\nfilterwarnings =\n    error::DeprecationWarning\n"
        path.write_text(text, encoding="utf-8")
        print("[PATCH] pytest.ini")
    else:
        write_file(path, PYTEST_INI)


def main() -> None:
    print("=== Applying Buster v6.5.1 Maintenance + Modernization ===")

    write_file(ROOT / "buster" / "utils" / "__init__.py", UTILS_INIT)
    write_file(ROOT / "buster" / "utils" / "datetime_utils.py", DATETIME_UTILS)
    write_file(ROOT / "buster" / "utils" / "json_utils.py", JSON_UTILS)
    write_file(ROOT / "buster" / "utils" / "logger.py", LOGGER_UTILS)

    # Patch known offender first, then broad scan.
    patch_autonomy_records_directly()
    changed = patch_utcnow_usage()

    write_file(ROOT / "test_v6_5_1_maintenance_modernization.py", TEST_CODE)
    write_file(ROOT / "BUSTER_V6_5_1_MAINTENANCE.md", """
# Buster v6.5.1 Maintenance + Modernization

This release cleans the v6 platform foundation before live voice and deeper runtime work.

## Adds

- `buster.utils.datetime_utils`
- `buster.utils.json_utils`
- `buster.utils.logger`
- Modern UTC timestamp helpers
- Atomic JSON persistence helpers
- Shared logger helper
- DeprecationWarning test guard
- Source scan to prevent `datetime.utcnow()` coming back

## Goal

Keep Buster warning-free and Python 3.12+ ready before v6.6 Live Voice Companion.
""")

    # Keep this last so pytest runs strict after code is fixed.
    ensure_pytest_ini()

    print("\nChanged files patched for utcnow:")
    if changed:
        for item in changed:
            print(f" - {item}")
    else:
        print(" - none found by broad scan")

    print("\nSUCCESS: v6.5.1 maintenance script applied.")
    print('Next: python -m pytest')
    print('Then: scripts\\\\test_push.bat "v6.5.1 maintenance modernization"')


if __name__ == "__main__":
    main()
