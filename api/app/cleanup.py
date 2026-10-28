from sqlalchemy import delete, func

from app.core.database import SessionLocal
from app.core.models import AnonymousSession, ImportPreview


def cleanup_expired() -> dict[str, int]:
    with SessionLocal() as db:
        now = func.now()
        expired_imports = (
            db.execute(delete(ImportPreview).where(ImportPreview.expires_at < now)).rowcount or 0
        )
        expired_sessions = (
            db.execute(delete(AnonymousSession).where(AnonymousSession.expires_at < now)).rowcount
            or 0
        )
        db.commit()
        return {
            "expired_sessions_deleted": expired_sessions,
            "expired_import_previews_deleted": expired_imports,
        }


if __name__ == "__main__":
    print(cleanup_expired())
