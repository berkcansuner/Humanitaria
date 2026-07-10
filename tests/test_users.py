"""Tests for the user + session auth data layer (rag/users.py)."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def users(tmp_path):
    """rag.users with the shared DB engine pointed at a throwaway SQLite DB."""
    settings = MagicMock()
    settings.DATABASE_URL = ""
    settings.CONVERSATION_DB_PATH = str(tmp_path / "auth.db")
    with patch("rag.db.get_settings", return_value=settings):
        from rag import users as users_mod
        yield users_mod


def test_create_user_and_fetch_by_email(users):
    uid = users.create_user("alice@example.com", "Alice", password="s3cret-pw")
    row = users.get_user_by_email("alice@example.com")
    assert row is not None
    assert row["id"] == uid
    assert row["email"] == "alice@example.com"
    assert row["name"] == "Alice"
    assert row["auth_provider"] == "password"


def test_get_user_by_id(users):
    uid = users.create_user("bob@example.com", "Bob", password="pw-123456")
    assert users.get_user_by_id(uid)["email"] == "bob@example.com"


def test_unknown_email_returns_none(users):
    assert users.get_user_by_email("nobody@example.com") is None


def test_duplicate_email_raises(users):
    from sqlalchemy.exc import IntegrityError

    users.create_user("dup@example.com", "First", password="pw-123456")
    with pytest.raises(IntegrityError):
        users.create_user("dup@example.com", "Second", password="pw-abcdef")


def test_password_is_hashed_not_plaintext(users):
    users.create_user("carol@example.com", "Carol", password="plaintext-pw")
    row = users.get_user_by_email("carol@example.com")
    assert row["password_hash"] != "plaintext-pw"
    assert "plaintext-pw" not in row["password_hash"]


def test_verify_password(users):
    users.create_user("dave@example.com", "Dave", password="correct-horse")
    row = users.get_user_by_email("dave@example.com")
    assert users.verify_password("correct-horse", row["password_hash"]) is True
    assert users.verify_password("wrong-password", row["password_hash"]) is False


def test_session_roundtrip_returns_user(users):
    uid = users.create_user("erin@example.com", "Erin", password="pw-123456")
    token = users.create_session(uid)
    assert isinstance(token, str) and token
    user = users.get_user_by_session(token)
    assert user is not None
    assert user["id"] == uid


def test_session_token_not_stored_in_plaintext(users, tmp_path):
    """The raw cookie token must not be recoverable from the DB (stored hashed)."""
    import sqlite3

    uid = users.create_user("frank@example.com", "Frank", password="pw-123456")
    token = users.create_session(uid)
    conn = sqlite3.connect(str(tmp_path / "auth.db"))
    rows = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()
    flat = " ".join(str(c) for r in rows for c in r)
    assert token not in flat


def test_unknown_session_returns_none(users):
    assert users.get_user_by_session("not-a-real-token") is None


def test_expired_session_returns_none(users):
    uid = users.create_user("gina@example.com", "Gina", password="pw-123456")
    token = users.create_session(uid, ttl_hours=-1)  # already expired
    assert users.get_user_by_session(token) is None


def test_delete_session_invalidates(users):
    uid = users.create_user("hank@example.com", "Hank", password="pw-123456")
    token = users.create_session(uid)
    users.delete_session(token)
    assert users.get_user_by_session(token) is None


def test_get_or_create_google_user_is_idempotent(users):
    first = users.get_or_create_google_user("google-sub-1", "gmail@example.com", "GUser")
    second = users.get_or_create_google_user("google-sub-1", "gmail@example.com", "GUser")
    assert first["id"] == second["id"]
    assert first["auth_provider"] == "google"
    assert first["google_sub"] == "google-sub-1"


def test_google_user_links_to_existing_email(users):
    """A user who signed up with a password and later logs in with Google (same
    email) should be linked to the existing account, not crash on UNIQUE email."""
    uid = users.create_user("shared@example.com", "Shared", password="pw-123456")
    linked = users.get_or_create_google_user("sub-xyz", "shared@example.com", "Shared")
    assert linked["id"] == uid
    assert linked["google_sub"] == "sub-xyz"


def test_google_user_links_case_insensitively(users):
    """Google may return the email in a different case than the stored (lowercased)
    password account. Normalising avoids a silent account split / missed link."""
    uid = users.create_user("shared@example.com", "Shared", password="pw-123456")
    linked = users.get_or_create_google_user("sub-xyz", "Shared@Example.COM", "Shared")
    assert linked["id"] == uid
    assert linked["email"] == "shared@example.com"
