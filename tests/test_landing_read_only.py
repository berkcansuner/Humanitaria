"""The read-only guarantees of the landing scripts that read the live database:
use_read_only_db (scripts/generate_landing_answer.py) and _read_only_connection
(scripts/build_landing_snapshot.py). They must never run rag.db's schema setup
(ALTER/CREATE/REVOKE) and must open Postgres transactions read-only. Temp SQLite
and never-connected engines only; no real database."""
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect

from rag import db

PG_URL = "postgresql+psycopg://user:pw@127.0.0.1:1/never_connected"


@pytest.fixture
def schema_spy(monkeypatch):
    """Fails the test if rag.db's schema setup runs; restores rag.db afterwards."""
    spy = MagicMock(side_effect=AssertionError("_ensure_schema must not run"))
    monkeypatch.setattr(db, "_ensure_schema", spy)
    monkeypatch.setattr(db, "_engines", {})
    return spy


def test_use_read_only_db_hands_out_an_engine_without_schema_setup(schema_spy):
    from scripts.generate_landing_answer import use_read_only_db

    use_read_only_db()
    engine = db.get_engine()
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    schema_spy.assert_not_called()
    assert inspect(engine).get_table_names() == []   # nothing was created
    engine.dispose()


def test_use_read_only_db_makes_postgres_transactions_read_only(schema_spy, monkeypatch):
    from scripts.generate_landing_answer import use_read_only_db

    monkeypatch.setattr(db, "_db_url", lambda: PG_URL)
    use_read_only_db()
    engine = db.get_engine()   # the pre-registered engine; nothing connects
    assert engine is db._engines[PG_URL]
    assert engine.get_execution_options()["postgresql_readonly"] is True
    assert engine.pool._pre_ping is True
    schema_spy.assert_not_called()


def test_read_only_connection_reads_without_schema_setup(schema_spy, monkeypatch):
    from scripts.build_landing_snapshot import _read_only_connection

    get_engine = MagicMock(side_effect=AssertionError("get_engine must not be used"))
    monkeypatch.setattr(db, "get_engine", get_engine)
    with _read_only_connection() as conn:
        assert conn.exec_driver_sql("SELECT 1").scalar() == 1
    schema_spy.assert_not_called()
    get_engine.assert_not_called()


def test_read_only_connection_is_read_only_on_postgres(schema_spy, monkeypatch):
    import sqlalchemy

    from scripts.build_landing_snapshot import _read_only_connection

    raw_conn = MagicMock(name="connection")
    engine = MagicMock(name="engine")
    engine.dialect.name = "postgresql"

    @contextmanager
    def _connect():
        yield raw_conn

    engine.connect = _connect
    created = MagicMock(return_value=engine)
    monkeypatch.setattr(sqlalchemy, "create_engine", created)
    monkeypatch.setattr(db, "_db_url", lambda: PG_URL)

    with _read_only_connection() as conn:
        assert conn is raw_conn.execution_options.return_value
    raw_conn.execution_options.assert_called_once_with(postgresql_readonly=True)
    created.assert_called_once_with(PG_URL)
    engine.dispose.assert_called_once()
    schema_spy.assert_not_called()
