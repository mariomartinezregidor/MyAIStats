import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import SessionLocal, get_db
from backend.app.models.entities import User, UserSession

bearer_scheme = HTTPBearer(auto_error=False)

SESSION_DAYS = 30


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, hash_hex = stored.split("$", 2)
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=len(expected))
    return hmac.compare_digest(actual, expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> tuple[str, UserSession]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session = UserSession(
        user_id=user.id,
        token_hash=_token_hash(token),
        created_at=now,
        expires_at=now + timedelta(days=SESSION_DAYS),
        last_used_at=now,
        revoked=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session


def revoke_session(db: Session, token: str) -> None:
    h = _token_hash(token)
    session = db.scalar(select(UserSession).where(UserSession.token_hash == h))
    if session:
        session.revoked = True
        db.commit()


def _resolve_user_from_credentials(
    db: Session, credentials: HTTPAuthorizationCredentials | None
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
    token = credentials.credentials.strip()
    if not token:
        return None
    h = _token_hash(token)
    session = db.scalar(select(UserSession).where(UserSession.token_hash == h))
    if not session or session.revoked:
        return None
    now = datetime.now(UTC)
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        return None
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        return None
    session.last_used_at = now
    db.commit()
    return user


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User | None:
    return _resolve_user_from_credentials(db, credentials)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    user = _resolve_user_from_credentials(db, credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def bootstrap_admin() -> None:
    email_raw = settings.admin_email.strip()
    password = settings.admin_password
    if not email_raw or not password:
        return
    email = email_raw.lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                is_active=True,
                is_admin=True,
            )
            db.add(user)
        else:
            user.password_hash = hash_password(password)
            user.is_active = True
            user.is_admin = True
        db.commit()