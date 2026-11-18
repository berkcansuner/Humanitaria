"""The Postgres column migration in rag/db.py (_pg_add_missing_columns) without
a Postgres: a fake connection records every statement and answers the catalog
queries, so the decision logic (which ALTERs run, the lock timeout, what a
timeout does) is covered locally. tests/test_db_pg_schema.py runs the same
paths against a real Postgres when TEST_DATABASE_URL is set."""
import logging
from contextlib import contextmanager

import pytest
from sqlalchemy.exc import OperationalError

from rag import db

ALL_COLUMNS = {
    "users": {"id", "email", "name", "ui_language"},
    "reports": {"id", "report_type", "cover_image", "section_images", "previous_report_id"},
}


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalar(self):
        return self._rows[0][0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeConn:
    """Answers to_regclass / pg_attribute from `tables` ({name: column set});
    records every statement in `sql`. `fail_on` makes a matching statement raise."""

    def __init__(self, tables, fail_on=None, error=None):
        self.tables = tables
        self.sql = []
        self.fail_on = fail_on
        self.error = error

    def exec_driver_sql(self, statement):
        self.sql.append(statement)
        if self.fail_on and self.fail_on in statement:
            raise self.error
        for name, cols in self.tables.items():
            if statement == f"SELECT to_regclass('{name}')":
                return _Result([(name,)])
            if "pg_attribute" in statement and f"to_regclass('{name}')" in statement:
                return _Result([(c,) for c in sorted(cols)])
        return _Result([])


class _FakeEngine:
    def __init__(self, conn):
        self.conn = conn

    @contextmanager
    def begin(self):
        yield self.conn


def _alters(conn):
    return [s for s in conn.sql if s.startswith("ALTER")]


class _PgError(Exception):
    def __init__(self, sqlstate):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _db_error(sqlstate):
    return OperationalError("ALTER TABLE ...", {}, _PgError(sqlstate))


def test_steady_state_boot_issues_no_alter():
    conn = _FakeConn(ALL_COLUMNS)
    db._pg_migrate_columns(_FakeEngine(conn))
    assert _alters(conn) == []
    assert all(s.startswith(("SET LOCAL", "SELECT")) for s in conn.sql)


def test_lock_timeout_is_set_first():
    conn = _FakeConn(ALL_COLUMNS)
    db._pg_migrate_columns(_FakeEngine(conn))
    assert conn.sql[0] == "SET LOCAL lock_timeout = '5s'"


def test_only_missing_columns_are_altered():
    tables = {
        "users": {"id", "email", "name"},
        "reports": {"id", "report_type", "cover_image", "section_images"},
    }
    conn = _FakeConn(tables)
    db._pg_migrate_columns(_FakeEngine(conn))
    assert _alters(conn) == [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ui_language TEXT",
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS previous_report_id TEXT",
    ]


def test_new_database_is_left_to_create_all():
    conn = _FakeConn({})
    db._pg_migrate_columns(_FakeEngine(conn))
    assert _alters(conn) == []
    assert not any("pg_attribute" in s for s in conn.sql)


def test_lock_timeout_does_not_stop_the_start(caplog):
    conn = _FakeConn({"users": {"id"}, "reports": ALL_COLUMNS["reports"]},
                     fail_on="ALTER TABLE users", error=_db_error("55P03"))
    with caplog.at_level(logging.WARNING, logger="rag.db"):
        db._pg_migrate_columns(_FakeEngine(conn))
    assert "lock" in caplog.text.lower()
    assert "next start" in caplog.text


def test_other_database_errors_still_raise():
    conn = _FakeConn({"users": {"id"}, "reports": ALL_COLUMNS["reports"]},
                     fail_on="ALTER TABLE users", error=_db_error("42501"))
    with pytest.raises(OperationalError):
        db._pg_migrate_columns(_FakeEngine(conn))
