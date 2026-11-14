"""P13-02: state files (the reports cache) must be written
atomically (temp file + os.replace) so a crash mid-write never leaves a corrupt /
partial JSON that the reader then fails to parse."""
from pathlib import Path


def _record_write_paths(monkeypatch):
    """Record every Path.write_text target (still performing the real write)."""
    written: list[str] = []
    orig = Path.write_text

    def rec(self, *a, **k):
        written.append(str(self))
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", rec)
    return written


def test_reports_cache_write_is_atomic(tmp_path, monkeypatch):
    from ingestion import analytics
    cache = tmp_path / ".reports_cache.json"
    monkeypatch.setattr(analytics, "_cache_path", lambda: cache)
    monkeypatch.setattr(
        analytics, "_state",
        analytics.ReportsCache(documents=[{"doc_id": "d1"}], namespace="", computed_at="t"),
    )
    written = _record_write_paths(monkeypatch)

    analytics._save_cache()

    assert any(p.endswith(".tmp") for p in written), "reports cache must be written via a temp file"
    assert cache.exists()
    assert not (tmp_path / ".reports_cache.json.tmp").exists()
