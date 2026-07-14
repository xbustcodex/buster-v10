from __future__ import annotations

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
