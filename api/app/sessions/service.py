import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.models import AnonymousSession


def now_utc() -> datetime:
    return datetime.now(UTC)


def create_session(db: Session) -> tuple[AnonymousSession, str]:
    credential = secrets.token_urlsafe(32)
    session = AnonymousSession(
        credential_hash=hashlib.sha256(credential.encode()).hexdigest(),
        expires_at=now_utc() + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, credential


def resolve_session(
    db: Session, credential: str | None, for_update: bool = False
) -> AnonymousSession:
    if not credential:
        raise DomainError("session_required", "Create or recover an anonymous session first.", 401)
    digest = hashlib.sha256(credential.encode()).hexdigest()
    query = select(AnonymousSession).where(AnonymousSession.credential_hash == digest)
    if for_update:
        query = query.with_for_update()
    session = db.scalar(query)
    if session is None:
        raise DomainError("session_invalid", "This session credential is not valid.", 401)
    if session.expires_at <= now_utc():
        raise DomainError("session_expired", "This session has expired. Start a new session.", 401)
    return session


def require_revision(session: AnonymousSession, expected: int | None) -> None:
    if expected is None:
        raise DomainError("revision_required", "Send the current input revision in If-Match.", 428)
    if expected != session.input_revision:
        raise DomainError(
            "revision_conflict",
            "These tasks changed in another request. Refresh before saving.",
            409,
            {"expected": expected, "current": session.input_revision},
        )
