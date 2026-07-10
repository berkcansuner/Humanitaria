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


# --- list_users (admin user list) ----------------------------------------

def test_list_users_returns_public_fields_newest_first(users):
    u1 = users.create_user("old@example.com", "Old", password="pw-123456")
    u2 = users.create_user("new@example.com", "New", password="pw-123456")
    rows, total = users.list_users()
    assert total == 2
    assert [r["id"] for r in rows] == [u2, u1] or rows[0]["created_at"] >= rows[1]["created_at"]
    for r in rows:
        assert set(r) == {"id", "email", "name", "auth_provider", "created_at", "last_login"}
        assert "password_hash" not in r and "google_sub" not in r


def test_list_users_search_matches_email_and_name_case_insensitive(users):
    users.create_user("alice@example.com", "Alice", password="pw-123456")
    users.create_user("bob@example.com", "Bob", password="pw-123456")
    rows, total = users.list_users(q="ALICE")
    assert total == 1 and rows[0]["email"] == "alice@example.com"
    rows, total = users.list_users(q="bo")   # name substring
    assert total == 1 and rows[0]["name"] == "Bob"


def test_list_users_pagination(users):
    for i in range(5):
        users.create_user(f"u{i}@example.com", f"User{i}", password="pw-123456")
    rows, total = users.list_users(offset=0, limit=2)
    assert total == 5 and len(rows) == 2
    rows2, _ = users.list_users(offset=4, limit=2)
    assert len(rows2) == 1


def test_list_users_last_login_from_sessions(users):
    uid = users.create_user("erin@example.com", "Erin", password="pw-123456")
    users.create_user("nologin@example.com", "NoLogin", password="pw-123456")
    users.create_session(uid)
    rows, _ = users.list_users()
    by_email = {r["email"]: r for r in rows}
    assert by_email["erin@example.com"]["last_login"] is not None
    assert by_email["nologin@example.com"]["last_login"] is None


# --- profile updates ----------------------------------------------------------

def test_update_user_name(users):
    uid = users.create_user("gina@example.com", "Gina", password="pw-123456")
    users.update_user_name(uid, "Gina Renamed")
    assert users.get_user_by_id(uid)["name"] == "Gina Renamed"


def test_change_password_rehashes(users):
    uid = users.create_user("hank@example.com", "Hank", password="old-pw-123")
    users.change_password(uid, "new-pw-456")
    row = users.get_user_by_id(uid)
    assert users.verify_password("new-pw-456", row["password_hash"]) is True
    assert users.verify_password("old-pw-123", row["password_hash"]) is False


def test_delete_user_sessions_keeps_the_given_token(users):
    uid = users.create_user("ivy@example.com", "Ivy", password="pw-123456")
    keep = users.create_session(uid)
    other = users.create_session(uid)
    users.delete_user_sessions(uid, keep_token=keep)
    assert users.get_user_by_session(keep) is not None
    assert users.get_user_by_session(other) is None


def test_delete_user_sessions_all(users):
    uid = users.create_user("jack@example.com", "Jack", password="pw-123456")
    t1 = users.create_session(uid)
    users.delete_user_sessions(uid)
    assert users.get_user_by_session(t1) is None


# --- account deletion ----------------------------------------------------------

def test_delete_user_account_removes_everything(users, tmp_path):
    """users + sessions (CASCADE) + conversations + messages (CASCADE) + reports
    must all go in one transaction; other users' data is untouched."""
    from rag import conversations as convs
    from rag import reports as reports_store

    uid = users.create_user("kate@example.com", "Kate", password="pw-123456")
    other = users.create_user("safe@example.com", "Safe", password="pw-123456")
    token = users.create_session(uid)
    convs.create_conversation(uid, "conv-kate", "Kate chat")
    convs.append_message("conv-kate", "user", "hello")
    convs.create_conversation(other, "conv-safe", "Safe chat")
    reports_store.create_report(
        "report-kate", uid, country="Mali", theme=None, date_from=None, date_to=None,
        language="en", title="Kate report", content="body", sources=[], doc_count=0,
    )

    deleted_convs = users.delete_user_account(uid)

    assert deleted_convs == ["conv-kate"]
    assert users.get_user_by_id(uid) is None
    assert users.get_user_by_session(token) is None
    assert convs.list_conversations(uid) == []
    assert convs.get_messages("conv-kate") == []
    assert reports_store.list_reports(uid) == []
    # other user untouched
    assert users.get_user_by_id(other) is not None
    assert [c["id"] for c in convs.list_conversations(other)] == ["conv-safe"]
