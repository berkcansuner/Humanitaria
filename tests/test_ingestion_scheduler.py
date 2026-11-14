import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestWatermark:
    def test_load_watermark_none_when_never_saved(self):
        from ingestion.scheduler import _load_watermark
        assert _load_watermark() is None

    def test_save_and_load_watermark(self):
        from ingestion.scheduler import _save_watermark, _load_watermark
        _save_watermark("2026-05-01")
        assert _load_watermark() == "2026-05-01"
        _save_watermark("2026-05-02T08:00:00+00:00")   # upsert, not a second row
        assert _load_watermark() == "2026-05-02T08:00:00+00:00"

    def test_load_watermark_survives_db_errors(self):
        from ingestion import scheduler
        with patch("rag.db.connect", side_effect=RuntimeError("db down")):
            assert scheduler._load_watermark() is None
            scheduler._save_watermark("2026-05-01")   # logged, not raised


class TestScheduledIngest:
    def test_scheduled_ingest_updates_watermark_on_success(self, tmp_path):
        with patch("ingestion.scheduler.run_pipeline") as mock_pipeline, \
             patch("ingestion.analytics.apply_retention"):
            mock_pipeline.return_value = {}
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            mock_pipeline.assert_called_once()
            from ingestion.scheduler import _load_watermark
            assert _load_watermark() is not None

    def test_scheduled_ingest_passes_date_from(self, tmp_path):
        from ingestion.scheduler import _save_watermark
        _save_watermark("2026-04-01")
        with patch("ingestion.scheduler.run_pipeline") as mock_pipeline, \
             patch("ingestion.analytics.apply_retention"):
            mock_pipeline.return_value = {}
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs.get("date_from") == "2026-04-01"

    def test_scheduled_ingest_passes_endpoints_from_settings(self, tmp_path):
        settings = MagicMock()
        settings.INGEST_ENDPOINTS = "reports,disasters"
        with patch("ingestion.scheduler.run_pipeline") as mock_pipeline, \
             patch("ingestion.analytics.apply_retention"), \
             patch("ingestion.runner.get_settings", return_value=settings):
            mock_pipeline.return_value = {}
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs.get("endpoints") == ["reports", "disasters"]

    def test_scheduled_ingest_does_not_update_watermark_on_failure(self, tmp_path):
        with patch("ingestion.scheduler.run_pipeline", side_effect=RuntimeError("oops")):
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            from ingestion.scheduler import _load_watermark
            assert _load_watermark() is None
