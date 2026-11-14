"""The ingest watermark must never move past a document that did not land.

Before the fix a failed embed/upsert batch was only counted, the watermark still
advanced to the run's start date, and the next incremental run (date_from =
watermark) never fetched those documents again. An incremental run cut off at its
limit lost the oldest new documents the same way (newest-first order). And on
Render the watermark file lived on a disk wiped on every sleep/deploy."""
from unittest.mock import MagicMock, patch

from ingestion import runner
from ingestion import scheduler as sched
from ingestion.pipeline import IngestionStats, run_pipeline


def _raw(i, created):
    return {"id": str(i), "fields": {"date": {"created": created}}}


def _run(items_per_call, *, date_from=None, limit=1000, embed=None):
    """run_pipeline with fetch returning the given pages, then []."""
    with patch("ingestion.pipeline.ReliefWebClient") as MockClient, \
         patch("ingestion.pipeline.parse", side_effect=lambda raw, ep: {"id": raw["id"], "body": "b"}), \
         patch("ingestion.pipeline.chunk_document", side_effect=lambda d: [{"id": d["id"] + "_0", "content": "b"}]), \
         patch("ingestion.pipeline.get_embeddings") as mock_get_emb, \
         patch("ingestion.pipeline.get_store"):
        client = MagicMock()
        client.fetch.side_effect = [*items_per_call, []]
        MockClient.return_value = client
        mock_get_emb.return_value = MagicMock(
            embed_documents=embed or (lambda texts: [[0.1] for _ in texts]))
        stats = run_pipeline(limit=limit, date_from=date_from)["reports"]
    return stats, client


def test_failed_batch_holds_resume_point_at_its_earliest_document():
    calls = {"n": 0}

    def embed(texts):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("429 rate limited")
        return [[0.1] for _ in texts]

    pages = [[_raw(1, "2026-11-10T08:00:00+00:00")],
             [_raw(2, "2026-11-11T09:00:00+00:00"), _raw(3, "2026-11-11T07:00:00+00:00")],
             [_raw(4, "2026-11-12T10:00:00+00:00")]]
    stats, _ = _run(pages, date_from="2026-11-10", embed=embed)
    assert stats.failed == 2 and stats.succeeded == 2
    assert stats.resume_from == "2026-11-11T07:00:00+00:00"


def test_clean_run_has_no_resume_point():
    stats, _ = _run([[_raw(1, "2026-11-10T08:00:00+00:00")]], date_from="2026-11-10")
    assert stats.resume_from is None


def test_incremental_run_goes_oldest_first_and_resumes_after_its_limit():
    page = [_raw(1, "2026-11-10T08:00:00+00:00"), _raw(2, "2026-11-10T09:00:00+00:00")]
    stats, client = _run([page], date_from="2026-11-09", limit=2)
    assert client.fetch.call_args.kwargs["sort"] == "date.created:asc"
    assert stats.resume_from == "2026-11-10T09:00:00+00:00"


def test_full_run_keeps_newest_first_and_does_not_resume_past_its_limit():
    page = [_raw(1, "2026-11-10T09:00:00+00:00"), _raw(2, "2026-11-10T08:00:00+00:00")]
    stats, client = _run([page], limit=2)
    assert client.fetch.call_args.kwargs["sort"] is None   # endpoint default: newest first
    assert stats.resume_from is None


def test_runner_holds_watermark_at_earliest_unfinished_document():
    stats = {"reports": IngestionStats(endpoint="reports", failed=3, resume_from="2026-11-11T07:00:00+00:00"),
             "disasters": IngestionStats(endpoint="disasters")}
    with patch("ingestion.scheduler.run_pipeline", return_value=stats), \
         patch("ingestion.analytics.apply_retention"):
        assert runner.run_ingest_once("manual") is True
    assert sched._load_watermark() == "2026-11-11T07:00:00+00:00"
    assert "resumes from 2026-11-11T07:00:00+00:00" in runner.get_state()["last_error"]


def test_runner_advances_watermark_when_everything_landed():
    stats = {"reports": IngestionStats(endpoint="reports", succeeded=5)}
    with patch("ingestion.scheduler.run_pipeline", return_value=stats), \
         patch("ingestion.analytics.apply_retention"):
        runner.run_ingest_once("manual")
    wm = sched._load_watermark()
    assert wm and len(wm) == 10   # the run's (UTC) start date
    assert runner.get_state()["last_error"] is None


def test_postgres_tables_are_closed_to_the_supabase_data_api():
    from rag import db
    conn = MagicMock()
    conn.exec_driver_sql.side_effect = lambda sql: [("anon",), ("authenticated",)] if "pg_roles" in sql else None
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    db._close_supabase_data_api(engine)
    sql = [c.args[0] for c in conn.exec_driver_sql.call_args_list]
    assert 'ALTER TABLE "ingest_state" ENABLE ROW LEVEL SECURITY' in sql
    revoke = next(s for s in sql if s.startswith("REVOKE"))
    assert '"ingest_state"' in revoke and '"users"' in revoke
    assert revoke.endswith("FROM anon, authenticated")


def test_supabase_lockdown_failure_is_not_fatal():
    from rag import db
    engine = MagicMock()
    engine.begin.side_effect = RuntimeError("permission denied")
    db._close_supabase_data_api(engine)   # logged, not raised
