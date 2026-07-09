"""Regression tests for the security-header middleware (P14-02).

The app must send baseline hardening headers (nosniff, frame-ancestors/X-Frame-Options,
Referrer-Policy, a CSP) on its responses. The CSP is tuned for the built Vite SPA
(external module script from /assets = 'self'; Vue inline styles = 'unsafe-inline').
"""
from fastapi.testclient import TestClient

from api.main import app


def test_security_headers_present_on_response():
    client = TestClient(app)          # not used as a context manager → no lifespan warmup
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
