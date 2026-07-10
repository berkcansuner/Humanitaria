"""Tests for the shared DB engine layer (rag/db.py)."""
from unittest.mock import MagicMock, patch

from rag import db


def _settings(database_url="", db_path="./conversations.db"):
    s = MagicMock()
    s.DATABASE_URL = database_url
    s.CONVERSATION_DB_PATH = db_path
    return s


def test_db_url_defaults_to_sqlite_file():
    with patch("rag.db.get_settings", return_value=_settings(db_path="/tmp/x.db")):
        assert db._db_url() == "sqlite:////tmp/x.db"


def test_db_url_forces_psycopg_driver():
    """Dashboard-copied postgresql:// / postgres:// URLs must map to psycopg3."""
    for prefix in ("postgresql://", "postgres://"):
        with patch("rag.db.get_settings",
                   return_value=_settings(database_url=f"{prefix}u:p@host:5432/db")):
            assert db._db_url() == "postgresql+psycopg://u:p@host:5432/db"


def test_db_url_passes_through_explicit_driver():
    url = "postgresql+psycopg://u:p@host:5432/db"
    with patch("rag.db.get_settings", return_value=_settings(database_url=url)):
        assert db._db_url() == url


def test_engine_cached_per_url(tmp_path):
    with patch("rag.db.get_settings",
               return_value=_settings(db_path=str(tmp_path / "a.db"))):
        assert db.get_engine() is db.get_engine()


def test_sqlite_legacy_conversations_gain_user_id_column(tmp_path):
    """A pre-auth SQLite file without conversations.user_id is migrated on first
    engine creation (before index creation, which needs the column)."""
    import sqlite3

    path = tmp_path / "legacy.db"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    con.commit()
    con.close()

    with patch("rag.db.get_settings", return_value=_settings(db_path=str(path))):
        engine = db.get_engine()
        with engine.connect() as conn:
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(conversations)")}
    assert "user_id" in cols


def test_sqlite_legacy_reports_gain_report_type_column(tmp_path):
    """A pre-report-types SQLite file without reports.report_type is migrated on
    first engine creation."""
    import sqlite3

    path = tmp_path / "legacy_reports.db"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE reports (id TEXT PRIMARY KEY, user_id TEXT, country TEXT, "
        "theme TEXT, date_from TEXT, date_to TEXT, language TEXT, title TEXT NOT NULL, "
        "content TEXT NOT NULL, sources_json TEXT, doc_count INTEGER, created_at TEXT NOT NULL)"
    )
    con.commit()
    con.close()

    with patch("rag.db.get_settings", return_value=_settings(db_path=str(path))):
        engine = db.get_engine()
        with engine.connect() as conn:
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(reports)")}
    assert "report_type" in cols
