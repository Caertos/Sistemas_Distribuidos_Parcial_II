from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from sqlalchemy.orm import Session
from src.models.refresh_token import RefreshToken


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: str, expires_days: int = 30) -> str:
    """Crea y guarda un refresh token (almacenando su hash) y devuelve el token crudo."""
    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=expires_days)
    rt = RefreshToken(token_hash=token_hash, user_id=str(user_id), expires_at=expires_at)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return token


def _get_by_hash(db: Session, token: str):
    return db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(token)).first()


def verify_refresh_token(db: Session, token: str):
    rt = _get_by_hash(db, token)
    if not rt:
        return None
    if rt.revoked:
        return None
    # `rt.expires_at` is timezone-aware (from Postgres). Compare using
    # an aware datetime to avoid TypeError when comparing naive vs aware.
    now = datetime.now(tz=timezone.utc)
    if rt.expires_at and rt.expires_at < now:
        return None
    return rt


def revoke_refresh_token(db: Session, token: str) -> bool:
    rt = _get_by_hash(db, token)
    if not rt:
        return False
    rt.revoked = True
    db.add(rt)
    db.commit()
    return True
