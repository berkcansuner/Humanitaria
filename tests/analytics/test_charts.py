import base64
from analytics.charts import trend_chart, comparison_chart, correlation_chart


def _is_png_datauri(s: str) -> bool:
    assert s.startswith("data:image/png;base64,")
    raw = base64.b64decode(s.split(",", 1)[1])
    return raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) > 500


def test_trend_chart_returns_png():
    s = trend_chart(["2025-01", "2025-02", "2025-03", "2025-04"],
                    [10, 20, 30, 40], slope=10.0, intercept=10.0,
                    title="IDP trend", ylabel="Kişi")
    assert _is_png_datauri(s)


def test_trend_chart_without_regression_line():
    s = trend_chart(["2025-01", "2025-02"], [10, 20],
                    slope=None, intercept=None, title="x", ylabel="y")
    assert _is_png_datauri(s)


def test_comparison_chart_returns_png():
    s = comparison_chart(["North", "South", "East"], [120, 30, 55],
                         title="Bölge", ylabel="Kişi")
    assert _is_png_datauri(s)


def test_correlation_chart_returns_png():
    s = correlation_chart([1, 2, 3, 4], [2, 4, 6, 8],
                          xlabel="A", ylabel="B", title="Korelasyon")
    assert _is_png_datauri(s)
