"""The Postgres column migration (rag/db.py _pg_migrate_columns) against a real
Postgres. Runs when TEST_DATABASE_URL points at a disposable Postgres (CI: the
pgvector service); skipped otherwise. Everything happens in a throwaway schema
put first on search_path, so the public tables other tests use are untouched."""
import logging
import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event

from rag import db

PG_URL = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_DATABASE_URL not set")

if "supabase" in PG_URL:
    raise RuntimeError("TEST_DATABASE_URL must be a disposable local Postgres, not Supabase")

SCHEMA = "schema_guard_test"


def _url():
    for prefix in ("postgresql://", "postgres://"):
        if PG_URL.startswith(prefix):
            return "postgresql+psycopg://" + PG_URL[len(prefix):]
    return PG_URL


@pytest.fixture
def engine():
    setup = create_engine(_url())
    with setup.begin() as conn:
        conn.exec_driver_sql(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        conn.exec_driver_sql(f"CREATE SCHEMA {SCHEMA}")
        # The tables as first deployed, before the migrated columns existed.
        conn.exec_driver_sql(f"CREATE TABLE {SCHEMA}.users (id TEXT PRIMARY KEY, email TEXT)")
        conn.exec_driver_sql(f"CREATE TABLE {SCHEMA}.reports (id TEXT PRIMARY KEY, title TEXT)")
    eng = create_engine(_url(), connect_args={"options": f"-csearch_path={SCHEMA}"})
    yield eng
    eng.dispose()
    with setup.begin() as conn:
        conn.exec_driver_sql(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    setup.dispose()


def _columns(eng, table):
    with eng.connect() as conn:
        return {r[0] for r in conn.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_schema = '{SCHEMA}' AND table_name = '{table}'")}


def _record(eng):
    statements = []
    event.listen(eng, "before_cursor_execute",
                 lambda conn, cur, statement, *a: statements.append(statement))
    return statements


def test_missing_columns_are_added_then_left_alone(engine):
    first = _record(engine)
    db._pg_migrate_columns(engine)
    assert first[0] == "SET LOCAL lock_timeout = '5s'"
    assert "ui_language" in _columns(engine, "users")
    assert {"report_type", "cover_image", "section_images"} <= _columns(engine, "reports")
    assert "previous_report_id" not in _columns(engine, "reports")

    first.clear()
    db._pg_migrate_columns(engine)
    assert first and not [s for s in first if s.lstrip().upper().startswith("ALTER")]


def test_the_removed_series_column_is_dropped_keeping_rows(engine):
    """Report series were removed (2026-11-26): a deployed reports table that still has
    previous_report_id loses it, and its rows stay."""
    with engine.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN previous_report_id TEXT")
        conn.exec_driver_sql("INSERT INTO reports (id, title, previous_report_id) "
                             "VALUES ('r1', 't', 'r0')")
    db._pg_migrate_columns(engine)
    assert "previous_report_id" not in _columns(engine, "reports")
    with engine.connect() as conn:
        assert [r[0] for r in conn.exec_driver_sql("SELECT id FROM reports")] == ["r1"]


def test_lock_timeout_gives_up_and_next_start_retries(engine, caplog):
    holder = engine.connect()
    holder.begin()
    holder.exec_driver_sql("SELECT 1 FROM users")  # ACCESS SHARE until rollback
    try:
        with patch.object(db, "_DDL_LOCK_TIMEOUT", "200ms"), \
             caplog.at_level(logging.WARNING, logger="rag.db"):
            db._pg_migrate_columns(engine)
        assert "ui_language" not in _columns(engine, "users")
        assert "next start" in caplog.text
    finally:
        holder.rollback()
        holder.close()
    db._pg_migrate_columns(engine)
    assert "ui_language" in _columns(engine, "users")
