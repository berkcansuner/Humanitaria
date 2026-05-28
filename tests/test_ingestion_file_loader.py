import pytest
from unittest.mock import patch, MagicMock
from ingestion.file_loader import strip_html, fetch_pdf_text


class TestStripHtml:
    def test_plain_text_unchanged(self):
        assert strip_html("hello world") == "hello world"

    def test_removes_tags(self):
        result = strip_html("<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "world" in result
        assert "<" not in result

    def test_removes_script_content(self):
        result = strip_html("<script>alert('xss')</script><p>safe</p>")
        assert "alert" not in result
        assert "safe" in result

    def test_removes_style_content(self):
        result = strip_html("<style>.cls{color:red}</style><p>visible</p>")
        assert "color" not in result
        assert "visible" in result

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_whitespace_collapsed(self):
        result = strip_html("<p>  hello  </p>  <p>  world  </p>")
        assert "  " not in result


class TestFetchPdfText:
    def test_returns_none_on_http_error(self):
        with patch("ingestion.file_loader.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=404,
                raise_for_status=lambda: (_ for _ in ()).throw(
                    __import__("requests").HTTPError("404")
                ),
            )
            result = fetch_pdf_text("http://example.com/missing.pdf")
            assert result is None

    def test_returns_extracted_text(self):
        with patch("ingestion.file_loader.requests.get") as mock_get, \
             patch("ingestion.file_loader.PdfReader") as MockReader, \
             patch("ingestion.file_loader.PdfReader", MockReader):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.content = b"%PDF-fake"
            mock_get.return_value = mock_resp

            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Extracted text content"
            MockReader.return_value.pages = [mock_page]

            import ingestion.file_loader as fl
            original = fl.PdfReader
            fl.PdfReader = MockReader
            try:
                result = fetch_pdf_text("http://example.com/doc.pdf")
            finally:
                fl.PdfReader = original
            assert result == "Extracted text content"

    def test_returns_none_on_empty_pdf(self):
        from unittest.mock import MagicMock
        mock_reader_cls = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader_cls.return_value.pages = [mock_page]

        import ingestion.file_loader as fl
        original = fl.PdfReader

        with patch("ingestion.file_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.content = b"%PDF-empty"
            mock_get.return_value = mock_resp
            fl.PdfReader = mock_reader_cls
            try:
                result = fetch_pdf_text("http://example.com/empty.pdf")
            finally:
                fl.PdfReader = original
        assert result is None
