"""User accounts + login sessions.

Backs the login/signup auth system. Mirrors ``rag/conversations.py``: plain SQL
through the shared engine in ``rag/db.py`` (SQLite file by default, Postgres
when ``DATABASE_URL`` is set), all functions synchronous — FastAPI routes
offload them with ``anyio.to_thread.run_sync``.

Passwords are hashed with bcrypt. Session cookies hold a high-entropy random
token; the DB stores only its SHA-256 hash, so a DB leak does not expose live
session cookies.
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import text

from rag.db import connect as _connect

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# A fixed bcrypt hash of a throwaway secret. login() verifies against this when an
# email is unknown (or the account is password-less, e.g. Google-only), so a failed
# login takes the same time whether or not the email is registered — closing the
# timing side-channel that would otherwise let an attacker enumerate accounts.
DUMMY_PASSWORD_HASH = hash_password("constant-time-login-placeholder")


# --- users ------------------------------------------------------------------

def create_user(
    email: str,
    name: str,
    password: str | None = None,
    auth_provider: str = "password",
    google_sub: str | None = None,
) -> str:
    """Create a user and return its id. Raises sqlalchemy.exc.IntegrityError on
    a duplicate email or google_sub."""
    uid = uuid.uuid4().hex
    pw_hash = hash_password(password) if password else None
    with _connect() as conn:
        conn.execute(
            text(
                "INSERT INTO users(id, email, name, password_hash, auth_provider, google_sub, created_at) "
                "VALUES (:id, :email, :name, :pw, :provider, :sub, :now)"
            ),
            {"id": uid, "email": email, "name": name, "pw": pw_hash,
             "provider": auth_provider, "sub": google_sub, "now": _now().isoformat()},
        )
    return uid


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE email = :email"), {"email": email}
        ).mappings().fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE id = :id"), {"id": user_id}
        ).mappings().fetchone()
    return dict(row) if row else None


def get_or_create_google_user(google_sub: str, email: str, name: str) -> dict:
    """Resolve a Google account to a local user. Matches by google_sub, then by
    email (linking the Google identity to a pre-existing password account), else
    creates a new google-provider user."""
    # Normalise the email the same way password signup/login does (strip + lower),
    # so a case difference from Google never splits into a second account or misses
    # the link to an existing password account.
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE google_sub = :sub"), {"sub": google_sub}
        ).mappings().fetchone()
        if row:
            return dict(row)
        row = conn.execute(
            text("SELECT * FROM users WHERE email = :email"), {"email": email}
        ).mappings().fetchone()
        if row:
            conn.execute(
                text("UPDATE users SET google_sub = :sub WHERE id = :id"),
                {"sub": google_sub, "id": row["id"]},
            )
            updated = conn.execute(
                text("SELECT * FROM users WHERE id = :id"), {"id": row["id"]}
            ).mappings().fetchone()
            return dict(updated)
        uid = uuid.uuid4().hex
        conn.execute(
            text(
                "INSERT INTO users(id, email, name, password_hash, auth_provider, google_sub, created_at) "
                "VALUES (:id, :email, :name, NULL, 'google', :sub, :now)"
            ),
            {"id": uid, "email": email, "name": name, "sub": google_sub,
             "now": _now().isoformat()},
        )
        created = conn.execute(
            text("SELECT * FROM users WHERE id = :id"), {"id": uid}
        ).mappings().fetchone()
    return dict(created)


# --- sessions ---------------------------------------------------------------

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: str, ttl_hours: int = 24) -> str:
    """Create a session and return the raw token (the cookie value). Only the
    token's SHA-256 hash is persisted."""
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(hours=ttl_hours)
    with _connect() as conn:
        conn.execute(
            text(
                "INSERT INTO sessions(token_hash, user_id, expires_at, created_at) "
                "VALUES (:th, :uid, :exp, :now)"
            ),
            {"th": _hash_token(token), "uid": user_id,
             "exp": expires_at.isoformat(), "now": _now().isoformat()},
        )
    return token


def get_user_by_session(token: str) -> dict | None:
    """Return the user for a valid, unexpired session token, else None."""
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            text(
                "SELECT u.*, s.expires_at FROM sessions s "
                "JOIN users u ON u.id = s.user_id WHERE s.token_hash = :th"
            ),
            {"th": _hash_token(token)},
        ).mappings().fetchone()
    if not row:
        return None
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at <= _now():
        return None
    user = dict(row)
    user.pop("expires_at", None)
    return user


def delete_session(token: str) -> None:
    with _connect() as conn:
        conn.execute(
            text("DELETE FROM sessions WHERE token_hash = :th"),
            {"th": _hash_token(token)},
        )


# --- admin user list ----------------------------------------------------------

def list_users(q: str = "", offset: int = 0, limit: int = 50) -> tuple[list[dict], int]:
    """Public user rows (no password_hash/google_sub), newest first, with the
    last session-creation time as ``last_login``. Returns (rows, total). Works
    on both dialects: correlated subquery instead of GROUP BY, LOWER+LIKE for
    case-insensitive search."""
    where = ""
    params: dict = {"limit": limit, "offset": offset}
    q = (q or "").strip().lower()
    if q:
        where = "WHERE LOWER(u.email) LIKE :pat OR LOWER(u.name) LIKE :pat"
        params["pat"] = f"%{q}%"
    with _connect() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM users u {where}"), params
        ).scalar_one()
        rows = conn.execute(
            text(
                "SELECT u.id, u.email, u.name, u.auth_provider, u.created_at, "
                "(SELECT MAX(s.created_at) FROM sessions s WHERE s.user_id = u.id) AS last_login "
                f"FROM users u {where} "
                "ORDER BY u.created_at DESC, u.id LIMIT :limit OFFSET :offset"
            ),
            params,
        ).mappings().all()
    return [dict(r) for r in rows], int(total)


# --- profile updates ----------------------------------------------------------

def update_user_name(user_id: str, name: str) -> None:
    with _connect() as conn:
        conn.execute(
            text("UPDATE users SET name = :name WHERE id = :id"),
            {"name": name, "id": user_id},
        )


def change_password(user_id: str, new_password: str) -> None:
    """Set a new bcrypt hash. Current-password verification is the route's job."""
    with _connect() as conn:
        conn.execute(
            text("UPDATE users SET password_hash = :pw WHERE id = :id"),
            {"pw": hash_password(new_password), "id": user_id},
        )


def delete_user_sessions(user_id: str, keep_token: str | None = None) -> None:
    """Drop the user's sessions; when ``keep_token`` (the raw cookie value) is
    given, that session survives — used by password change to keep the active
    session while logging out everywhere else."""
    params: dict = {"uid": user_id}
    sql = "DELETE FROM sessions WHERE user_id = :uid"
    if keep_token:
        sql += " AND token_hash != :keep"
        params["keep"] = _hash_token(keep_token)
    with _connect() as conn:
        conn.execute(text(sql), params)
