"""Shared database engine: SQLite by default, Postgres when DATABASE_URL is set.

One SQLAlchemy Core engine per database URL. The three stores
(``rag/users.py``, ``rag/conversations.py``, ``rag/reports.py``) share it and
keep issuing plain SQL via ``text()`` — the SQL used is valid in both dialects
(named binds, ``ON CONFLICT DO NOTHING``, ``RETURNING id``), so there is a
single code path for tests/dev (SQLite file) and production (Supabase Postgres).

The schema is created once per engine (``metadata.create_all``), replacing the
old run-on-every-connection ``_ensure_schema`` pattern, which would be a
DDL-per-request anti-pattern on Postgres.
"""
import logging
from contextlib import contextmanager

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from config import get_settings

logger = logging.getLogger(__name__)

metadata = MetaData()

# Schemas mirror the original SQLite DDL. Timestamps stay ISO-8601 TEXT so the
# existing string comparisons (e.g. session expiry) keep working unchanged.
users_table = Table(
    "users", metadata,
    Column("id", Text, primary_key=True),
    Column("email", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("password_hash", Text),
    Column("auth_provider", Text, nullable=False, server_default="password"),
    Column("google_sub", Text, unique=True),
    Column("created_at", Text, nullable=False),
)

sessions_table = Table(
    "sessions", metadata,
    Column("token_hash", Text, primary_key=True),
    Column("user_id", Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("expires_at", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)
Index("idx_sessions_user", sessions_table.c.user_id)

conversations_table = Table(
    "conversations", metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text),
    Column("title", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)
Index("idx_conversations_user", conversations_table.c.user_id)

messages_table = Table(
    "messages", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", Text,
           ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("role", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("sources_json", Text),
    Column("created_at", Text, nullable=False),
)
Index("idx_messages_conv", messages_table.c.conversation_id, messages_table.c.id)

reports_table = Table(
    "reports", metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text),
    Column("report_type", Text),
    Column("country", Text),
    Column("theme", Text),
    Column("date_from", Text),
    Column("date_to", Text),
    Column("language", Text),
    Column("title", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("sources_json", Text),
    Column("doc_count", Integer),
    Column("cover_image", Text),
    Column("section_images", Text),
    Column("created_at", Text, nullable=False),
)
Index("idx_reports_user", reports_table.c.user_id, reports_table.c.created_at)


_engines: dict[str, Engine] = {}


def _db_url() -> str:
    s = get_settings()
    url = s.DATABASE_URL
    if not url:
        return f"sqlite:///{s.CONVERSATION_DB_PATH}"
    # Dashboard connection strings say postgresql:// (or postgres://); SQLAlchemy
    # would pick the psycopg2 driver for those — force the installed psycopg3.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def get_engine() -> Engine:
    """Engine for the configured database, created (and schema-ensured) once per URL."""
    url = _db_url()
    engine = _engines.get(url)
    if engine is None:
        if url.startswith("sqlite"):
            # NullPool: no lingering file handles, so Windows tmp dirs (tests)
            # can be removed; check_same_thread off — calls come from AnyIO
            # worker threads.
            engine = create_engine(
                url, poolclass=NullPool, connect_args={"check_same_thread": False}
            )

            @event.listens_for(engine, "connect")
            def _sqlite_pragmas(dbapi_conn, _record):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.close()
        else:
            # pool_pre_ping revalidates connections the Supabase pooler may have
            # dropped while the free-tier instance slept.
            engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
        _ensure_schema(engine)
        _engines[url] = engine
    return engine


def _ensure_schema(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        # Migrate pre-auth SQLite files that lack conversations.user_id BEFORE
        # create_all, or the idx_conversations_user index creation would fail.
        # (Legacy rows keep user_id NULL → invisible to every user, safe default.)
        with engine.begin() as conn:
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(conversations)")}
            if cols and "user_id" not in cols:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN user_id TEXT")
            # Migrate pre-report-types SQLite files that lack reports.report_type.
            # (Legacy rows keep report_type NULL → normalized to "situation" on read.)
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(reports)")}
            if cols and "report_type" not in cols:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN report_type TEXT")
            if cols and "cover_image" not in cols:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN cover_image TEXT")
            if cols and "section_images" not in cols:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN section_images TEXT")
    else:
        # Postgres: same self-healing migration for an already-deployed reports
        # table (guard the ALTER on the table existing, since a brand-new
        # database has no reports table yet — create_all() below creates it
        # fresh, already including report_type).
        with engine.begin() as conn:
            exists = conn.exec_driver_sql(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'reports'"
            ).fetchone()
            if exists:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_type TEXT")
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN IF NOT EXISTS cover_image TEXT")
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN IF NOT EXISTS section_images TEXT")
    metadata.create_all(engine)


@contextmanager
def connect():
    """One transaction per store call: commits on success, rolls back on error."""
    with get_engine().begin() as conn:
        yield conn
