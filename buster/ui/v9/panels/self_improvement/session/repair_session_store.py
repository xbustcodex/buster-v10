from __future__ import annotations

from pathlib import Path

from .repair_session import RepairSession


class RepairSessionStore:
    """
    Persist and discover repair sessions.

    Default storage:

        <project_root>/data/self_improvement/sessions/<session_id>.json
    """

    def __init__(
        self,
        project_root: str | Path,
        sessions_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(
            project_root
        ).expanduser().resolve()

        self.sessions_root = (
            Path(sessions_root).expanduser().resolve()
            if sessions_root is not None
            else self.project_root
            / "data"
            / "self_improvement"
            / "sessions"
        )

        self.sessions_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def session_path(
        self,
        session_id: str,
    ) -> Path:
        safe_id = "".join(
            character
            for character in str(session_id)
            if character.isalnum()
            or character in {"-", "_"}
        )

        if not safe_id:
            raise ValueError("Invalid repair session ID.")

        return self.sessions_root / f"{safe_id}.json"

    def save(
        self,
        session: RepairSession,
    ) -> Path:
        return session.save(
            self.session_path(session.session_id)
        )

    def load(
        self,
        session_id: str,
    ) -> RepairSession:
        return RepairSession.load(
            self.session_path(session_id)
        )

    def delete(
        self,
        session_id: str,
    ) -> bool:
        path = self.session_path(session_id)

        if not path.exists():
            return False

        path.unlink()
        return True

    def list_sessions(
        self,
        *,
        include_completed: bool = True,
    ) -> list[RepairSession]:
        sessions: list[RepairSession] = []

        for path in self.sessions_root.glob("*.json"):
            try:
                session = RepairSession.load(path)
            except Exception:
                continue

            if not include_completed and session.is_complete:
                continue

            sessions.append(session)

        sessions.sort(
            key=lambda item: item.updated_at,
            reverse=True,
        )

        return sessions

    def latest(
        self,
        *,
        include_completed: bool = True,
    ) -> RepairSession | None:
        sessions = self.list_sessions(
            include_completed=include_completed
        )

        return sessions[0] if sessions else None

    def active_sessions(self) -> list[RepairSession]:
        return self.list_sessions(
            include_completed=False
        )


__all__ = [
    "RepairSessionStore",
]
