import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestWatermark:
    def test_load_watermark_none_when_file_missing(self, tmp_path):
        with patch("ingestion.scheduler._watermark_path", return_value=tmp_path / ".last_ingest.json"):
            from ingestion.scheduler import _load_watermark
            assert _load_watermark() is None

    def test_save_and_load_watermark(self, tmp_path):
        wm_path = tmp_path / ".last_ingest.json"
        with patch("ingestion.scheduler._watermark_path", return_value=wm_path):
            from ingestion.scheduler import _save_watermark, _load_watermark
            _save_watermark("2026-05-01")
            assert _load_watermark() == "2026-05-01"

    def test_load_watermark_handles_corrupt_file(self, tmp_path):
        wm_path = tmp_path / ".last_ingest.json"
        wm_path.write_text("not json", encoding="utf-8")
        with patch("ingestion.scheduler._watermark_path", return_value=wm_path):
            from ingestion.scheduler import _load_watermark
            assert _load_watermark() is None


class TestScheduledIngest:
    def test_scheduled_ingest_updates_watermark_on_success(self, tmp_path):
        wm_path = tmp_path / ".last_ingest.json"
        with patch("ingestion.scheduler._watermark_path", return_value=wm_path), \
             patch("ingestion.scheduler.run_pipeline") as mock_pipeline, \
             patch("ingestion.analytics.rebuild_documents"):
            mock_pipeline.return_value = {}
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            mock_pipeline.assert_called_once()
            assert wm_path.exists()

    def test_scheduled_ingest_passes_date_from(self, tmp_path):
        wm_path = tmp_path / ".last_ingest.json"
        wm_path.write_text(json.dumps({"last_ingest": "2026-04-01"}), encoding="utf-8")
        with patch("ingestion.scheduler._watermark_path", return_value=wm_path), \
             patch("ingestion.scheduler.run_pipeline") as mock_pipeline, \
             patch("ingestion.analytics.rebuild_documents"):
            mock_pipeline.return_value = {}
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs.get("date_from") == "2026-04-01"

    def test_scheduled_ingest_passes_endpoints_from_settings(self, tmp_path):
        wm_path = tmp_path / ".last_ingest.json"
        settings = MagicMock()
        settings.INGEST_ENDPOINTS = "reports,disasters"
        with patch("ingestion.scheduler._watermark_path", return_value=wm_path), \
             patch("ingestion.scheduler.run_pipeline") as mock_pipeline, \
             patch("ingestion.analytics.rebuild_documents"), \
             patch("ingestion.runner.get_settings", return_value=settings):
            mock_pipeline.return_value = {}
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs.get("endpoints") == ["reports", "disasters"]

    def test_scheduled_ingest_does_not_update_watermark_on_failure(self, tmp_path):
        wm_path = tmp_path / ".last_ingest.json"
        with patch("ingestion.scheduler._watermark_path", return_value=wm_path), \
             patch("ingestion.scheduler.run_pipeline", side_effect=RuntimeError("oops")):
            from ingestion.scheduler import _run_scheduled_ingest
            _run_scheduled_ingest()
            assert not wm_path.exists()
