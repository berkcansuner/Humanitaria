"""Tests for the shared ingest runner (ingestion/runner.py)."""
from unittest.mock import patch

from ingestion import runner
from ingestion.pipeline import IngestionStats


def test_run_ingest_once_skips_when_locked():
    """A second run while the lock is held returns False and never calls the pipeline."""
    assert runner._lock.acquire(blocking=False)
    try:
        with patch("ingestion.scheduler.run_pipeline") as mock_pipeline:
            assert runner.run_ingest_once("manual") is False
            mock_pipeline.assert_not_called()
    finally:
        runner._lock.release()


def test_run_ingest_once_runs_and_writes_watermark(tmp_path):
    wm = tmp_path / ".last_ingest.json"
    stats = {"reports": IngestionStats(endpoint="reports", total=5, succeeded=4, failed=0, skipped=1)}
    with patch("ingestion.scheduler._watermark_path", return_value=wm), \
         patch("ingestion.scheduler.run_pipeline", return_value=stats) as mock_pipeline:
        assert runner.run_ingest_once("manual") is True
        mock_pipeline.assert_called_once()
        assert wm.exists()
    state = runner.get_state()
    assert state["running"] is False
    assert state["source"] == "manual"
    assert state["last_error"] is None
    assert state["last_stats"]["reports"]["succeeded"] == 4


def test_run_ingest_once_records_error_and_skips_watermark(tmp_path):
    wm = tmp_path / ".last_ingest.json"
    with patch("ingestion.scheduler._watermark_path", return_value=wm), \
         patch("ingestion.scheduler.run_pipeline", side_effect=RuntimeError("boom")):
        # The pipeline error is handled (lock released), so the call still returns True;
        # the watermark is NOT advanced.
        assert runner.run_ingest_once("manual") is True
        assert not wm.exists()
    state = runner.get_state()
    assert state["running"] is False
    assert "boom" in state["last_error"]
