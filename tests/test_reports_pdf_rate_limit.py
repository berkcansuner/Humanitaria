"""P18-01: the PDF export endpoint runs xhtml2pdf/reportlab (CPU-heavy), so it must
be rate-limited like the other expensive endpoints — an authenticated user should
not be able to loop it and exhaust the single worker's CPU."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.limiter import limiter


def test_report_pdf_is_rate_limited():
    client = TestClient(app)
    limiter.enabled = True
    limiter.reset()
    try:
        with patch("api.routes.reports.get_settings",
                   return_value=MagicMock(RATE_LIMIT="1/minute")):
            first = client.get("/reports/nonexistent/pdf")
            second = client.get("/reports/nonexistent/pdf")
        assert first.status_code == 404    # no such report, but the attempt still counts
        assert second.status_code == 429   # second within the window is throttled
    finally:
        limiter.reset()
        limiter.enabled = False
