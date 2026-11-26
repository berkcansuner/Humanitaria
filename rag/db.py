"""Shared database engine: SQLite by default, Postgres when DATABASE_URL is set.

Postgres (production, Supabase) also holds the vector index: the ``chunks`` table
(pgvector ``halfvec`` embeddings, created by ``_ensure_vector_schema``) next to the
``documents`` table (one row per indexed report — the admin list and retention).

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
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError
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
    # Interface language ("en" | "tr"); NULL = never chosen on an account-linked device.
    Column("ui_language", Text),
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

# Small durable key/value state (e.g. the incremental-ingest watermark). It lives
# in the DB because Render's free-tier disk is wiped on every sleep/deploy.
ingest_state_table = Table(
    "ingest_state", metadata,
    Column("key", Text, primary_key=True),
    Column("value", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

# One row per indexed document, written with its chunks at ingest time. Serves the
# admin reports list, the report-form country list and retention with plain SQL —
# no scan of the vector index.
documents_table = Table(
    "documents", metadata,
    Column("doc_id", Text, primary_key=True),
    Column("title", Text, nullable=False, server_default=""),
    Column("url", Text, nullable=False, server_default=""),
    Column("source", Text, nullable=False, server_default=""),
    Column("country", Text, nullable=False, server_default=""),
    Column("doctype", Text, nullable=False, server_default=""),
    Column("date", Text, nullable=False, server_default=""),      # YYYY-MM-DD ('' = unknown)
    Column("updated_at", Text, nullable=False),
)
Index("idx_documents_date", documents_table.c.date)
Index("idx_documents_country", documents_table.c.country)


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
            # Migrate SQLite files that predate users.ui_language.
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(users)")}
            if cols and "ui_language" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN ui_language TEXT")
            # Migrate pre-report-types SQLite files that lack reports.report_type.
            # (Legacy rows keep report_type NULL → normalized to "situation" on read.)
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(reports)")}
            if cols and "report_type" not in cols:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN report_type TEXT")
            if cols and "cover_image" not in cols:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN cover_image TEXT")
            if cols and "section_images" not in cols:
                conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN section_images TEXT")
            # Report series were removed (2026-11-26): drop the link column.
            if "previous_report_id" in cols:
                conn.exec_driver_sql("ALTER TABLE reports DROP COLUMN previous_report_id")
    else:
        _pg_migrate_columns(engine)
    metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        _ensure_vector_schema(engine)
        _close_supabase_data_api(engine)


# Columns added after their table was first deployed: create_all() never alters
# an existing table, so an already-deployed Postgres database gains them here.
_PG_ADDED_COLUMNS = {
    "users": ("ui_language",),
    "reports": ("report_type", "cover_image", "section_images"),
}
# Columns of a removed feature, dropped from an already-deployed database (report
# series, 2026-11-26).
_PG_DROPPED_COLUMNS = {
    "reports": ("previous_report_id",),
}
# How long a start waits for a table lock before giving up on the migration.
_DDL_LOCK_TIMEOUT = "5s"
_LOCK_NOT_AVAILABLE = "55P03"  # SQLSTATE raised when lock_timeout expires


def _pg_migrate_columns(engine: Engine) -> None:
    """Add the columns in _PG_ADDED_COLUMNS that an existing table lacks, and drop
    the ones in _PG_DROPPED_COLUMNS that it still has.

    ``ADD COLUMN IF NOT EXISTS`` takes an ACCESS EXCLUSIVE lock before it checks,
    and ``users`` is read on every request, so the ALTER runs only for a column
    the catalog says is missing: a steady-state start takes no lock on the
    tables. A blocked ALTER gives up after _DDL_LOCK_TIMEOUT instead of queueing
    every session lookup behind it; the start then goes on without the column
    (reads use ``SELECT *``, saving the interface language answers 503) and the
    next start retries. Any other error still stops the start, as before."""
    try:
        with engine.begin() as conn:
            _pg_add_missing_columns(conn)
    except DBAPIError as e:
        if getattr(e.orig, "sqlstate", None) != _LOCK_NOT_AVAILABLE:
            raise
        logger.warning("Schema migration skipped: a table lock was not granted within %s; "
                       "missing columns are added on the next start", _DDL_LOCK_TIMEOUT)


def _pg_add_missing_columns(conn: Connection) -> None:
    conn.exec_driver_sql(f"SET LOCAL lock_timeout = '{_DDL_LOCK_TIMEOUT}'")
    for table, columns in _PG_ADDED_COLUMNS.items():
        # to_regclass resolves through search_path, like the ALTER below. NULL =
        # a brand-new database: create_all() creates the table complete.
        if not conn.exec_driver_sql(f"SELECT to_regclass('{table}')").scalar():
            continue
        present = {r[0] for r in conn.exec_driver_sql(
            "SELECT attname FROM pg_attribute "
            f"WHERE attrelid = to_regclass('{table}') AND attnum > 0 AND NOT attisdropped")}
        for column in columns:
            if column not in present:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} TEXT")
    for table, columns in _PG_DROPPED_COLUMNS.items():
        if not conn.exec_driver_sql(f"SELECT to_regclass('{table}')").scalar():
            continue
        present = {r[0] for r in conn.exec_driver_sql(
            "SELECT attname FROM pg_attribute "
            f"WHERE attrelid = to_regclass('{table}') AND attnum > 0 AND NOT attisdropped")}
        for column in columns:
            if column in present:
                conn.exec_driver_sql(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")


def _ensure_vector_schema(engine: Engine) -> None:
    """The pgvector chunk table (Postgres only — SQLite dev/test runs have no vector
    search). Embeddings are ``halfvec`` (2 bytes/dim): at EMBED_DIM=768 the whole
    corpus fits the Supabase free-tier 500 MB. Filter fields are real columns so the
    retriever's WHERE clause is plain SQL; ``metadata`` keeps the full chunk metadata
    returned to the RAG chain."""
    dim = int(get_settings().EMBED_DIM)
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        conn.exec_driver_sql(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id        TEXT PRIMARY KEY,
                doc_id    TEXT NOT NULL,
                content   TEXT NOT NULL,
                metadata  JSONB NOT NULL,
                embedding HALFVEC({dim}) NOT NULL,
                country   TEXT NOT NULL DEFAULT '',
                theme     TEXT NOT NULL DEFAULT '',
                themes    TEXT[],
                doctype   TEXT NOT NULL DEFAULT '',
                source    TEXT NOT NULL DEFAULT '',
                format    TEXT NOT NULL DEFAULT '',
                date_ts   INTEGER NOT NULL DEFAULT 0
            )""")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks (doc_id)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_chunks_country ON chunks (country)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_chunks_date ON chunks (date_ts)")
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks "
            "USING hnsw (embedding halfvec_cosine_ops)")


def _close_supabase_data_api(engine: Engine) -> None:
    """Supabase grants its public API roles (anon/authenticated) access to every new
    table in the public schema. The app talks to Postgres directly and never uses
    that API, so keep every app table (including ones added later) closed to it:
    RLS on with no policies, and the role grants revoked. Idempotent; a failure is
    logged, never fatal (plain Postgres has no such roles)."""
    tables = [t.name for t in metadata.sorted_tables] + ["chunks"]
    names = ", ".join(f'"{t}"' for t in tables)
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(f"SET LOCAL lock_timeout = '{_DDL_LOCK_TIMEOUT}'")
            for t in tables:
                # ENABLE ROW LEVEL SECURITY takes an ACCESS EXCLUSIVE lock even when
                # RLS is already on, so only tables still without it get the ALTER.
                if not conn.exec_driver_sql(
                        f"SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('{t}')").scalar():
                    conn.exec_driver_sql(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY')
            roles = [r[0] for r in conn.exec_driver_sql(
                "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")]
            if roles:
                conn.exec_driver_sql(f"REVOKE ALL ON {names} FROM {', '.join(roles)}")
    except Exception as e:
        logger.warning("Could not close app tables to the Supabase Data API: %s", e)


@contextmanager
def connect():
    """One transaction per store call: commits on success, rolls back on error."""
    with get_engine().begin() as conn:
        yield conn
