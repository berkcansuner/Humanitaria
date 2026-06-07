"""User accounts + login sessions (SQLite).

Backs the login/signup auth system. Mirrors ``rag/conversations.py``: plain
stdlib ``sqlite3``, same DB file (``CONVERSATION_DB_PATH``), one fresh
connection per call (WAL mode), all functions synchronous.

Passwords are hashed with bcrypt. Session cookies hold a high-entropy random
token; the DB stores only its SHA-256 hash, so a DB leak does not expose live
session cookies.
"""
import hashlib
import logging
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import bcrypt

from config import get_settings

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def _connect():
    conn = sqlite3.connect(get_settings().CONVERSATION_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT NOT NULL UNIQUE,
            name          TEXT NOT NULL,
            password_hash TEXT,
            auth_provider TEXT NOT NULL DEFAULT 'password',
            google_sub    TEXT UNIQUE,
            created_at    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """
    )


# --- password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# --- users ------------------------------------------------------------------

def create_user(
    email: str,
    name: str,
    password: str | None = None,
    auth_provider: str = "password",
    google_sub: str | None = None,
) -> str:
    """Create a user and return its id. Raises sqlite3.IntegrityError on a
    duplicate email or google_sub."""
    uid = uuid.uuid4().hex
    pw_hash = hash_password(password) if password else None
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users(id, email, name, password_hash, auth_provider, google_sub, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, email, name, pw_hash, auth_provider, google_sub, _now().isoformat()),
        )
    return uid


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_or_create_google_user(google_sub: str, email: str, name: str) -> dict:
    """Resolve a Google account to a local user. Matches by google_sub, then by
    email (linking the Google identity to a pre-existing password account), else
    creates a new google-provider user."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
        ).fetchone()
        if row:
            return dict(row)
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET google_sub = ? WHERE id = ?", (google_sub, row["id"])
            )
            updated = conn.execute(
                "SELECT * FROM users WHERE id = ?", (row["id"],)
            ).fetchone()
            return dict(updated)
        uid = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO users(id, email, name, password_hash, auth_provider, google_sub, created_at) "
            "VALUES (?, ?, ?, NULL, 'google', ?, ?)",
            (uid, email, name, google_sub, _now().isoformat()),
        )
        created = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
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
            "INSERT INTO sessions(token_hash, user_id, expires_at, created_at) "
            "VALUES (?, ?, ?, ?)",
            (_hash_token(token), user_id, expires_at.isoformat(), _now().isoformat()),
        )
    return token


def get_user_by_session(token: str) -> dict | None:
    """Return the user for a valid, unexpired session token, else None."""
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT u.* , s.expires_at FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
            (_hash_token(token),),
        ).fetchone()
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
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
