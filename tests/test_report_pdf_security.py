"""Security regression tests for M&E report PDF rendering (rag/report_pdf.py).

Guards P1-02: report `content` is LLM-generated and Python-Markdown passes raw HTML
through, so an `<img src="http://…">` in the body must NOT cause xhtml2pdf to make a
server-side request (SSRF) or read a local file when the PDF is generated.
"""
import socket
import threading
import time

from rag.report_pdf import render_report_pdf


def _count_fetch_attempts_for_body_img() -> int:
    """Render a report whose body embeds an <img> pointing at a local listener and
    return the number of inbound connections xhtml2pdf makes (0 = no SSRF)."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    srv.settimeout(0.3)
    port = srv.getsockname()[1]
    hits: list = []
    stop = threading.Event()

    def listener():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            hits.append(1)
            try:
                conn.recv(512)
                conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            finally:
                conn.close()

    t = threading.Thread(target=listener, daemon=True)
    t.start()
    report = {
        "country": "Testland", "theme": None, "date_from": "2024-01-01",
        "date_to": "2024-02-01", "language": "en",
        "content": f'Overview [1].\n\n<img src="http://127.0.0.1:{port}/ssrf-probe">\n\ntext.',
        "sources": [],
    }
    try:
        render_report_pdf(report)
        time.sleep(0.4)  # allow any in-flight fetch to land
    finally:
        stop.set()
        srv.close()
        t.join(timeout=2)
    return len(hits)


def test_report_pdf_does_not_fetch_remote_resources():
    assert _count_fetch_attempts_for_body_img() == 0, (
        "xhtml2pdf fetched a remote URL embedded in report content (SSRF)"
    )
