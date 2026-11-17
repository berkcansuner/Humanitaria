import base64
from analytics.charts import trend_chart, comparison_chart, correlation_chart


def _is_png_datauri(s: str) -> bool:
    assert s.startswith("data:image/png;base64,")
    raw = base64.b64decode(s.split(",", 1)[1])
    return raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) > 500


def test_trend_chart_returns_png():
    s = trend_chart(["2025-01", "2025-02", "2025-03", "2025-04"],
                    [10, 20, 30, 40], slope=10.0, intercept=10.0, unit="kişi")
    assert _is_png_datauri(s)


def test_trend_chart_without_regression_line():
    s = trend_chart(["2025-01", "2025-02"], [10, 20],
                    slope=None, intercept=None)
    assert _is_png_datauri(s)


def test_comparison_chart_returns_png():
    s = comparison_chart(["North", "South", "East"], [120, 30, 55])
    assert _is_png_datauri(s)


def test_correlation_chart_returns_png():
    s = correlation_chart([1, 2, 3, 4], [2, 4, 6, 8],
                          xlabel="A", ylabel="B")
    assert _is_png_datauri(s)


def test_trend_chart_accepts_language():
    s = trend_chart(["2025-01", "2025-02", "2025-03"], [1, 2, 3], slope=1.0, intercept=1.0,
                    language="en")
    assert _is_png_datauri(s)


def test_format_value_compacts_large_numbers_per_language():
    from analytics.charts import format_value
    assert format_value(2_500_000, "en") == "2.5M"
    assert format_value(2_500_000, "tr") == "2,5 mn"
    assert format_value(250_000, "en") == "250K"
    assert format_value(250_000, "tr") == "250 bin"
    assert format_value(1_200_000_000, "tr") == "1,2 mr"
    assert format_value(4_500, "en") == "4,500"      # full under 10,000
    assert format_value(4_500, "tr") == "4.500"
    assert format_value(0, "en") == "0"
    # Bar-tip labels keep three significant digits, not two decimals.
    assert format_value(929_250, "tr") == "929 bin"
    assert format_value(78_540, "en") == "78.5K"
    assert format_value(1_794_000, "en") == "1.79M"


def test_format_value_writes_shares_as_percent():
    from analytics.charts import format_value
    assert format_value(45, "en", percent=True) == "45%"
    assert format_value(42.5, "tr", percent=True) == "%42,5"


def test_trend_chart_on_iso_dates():
    s = trend_chart(["2022-04-01T00:00:00", "2023-06-01T00:00:00", "2024-04-01T00:00:00"],
                    [20, 35, 45], slope=10.0, intercept=25.0,
                    times=[0, 1.17, 2.0], language="tr", percent=True)
    assert _is_png_datauri(s)


def test_charts_draw_a_dark_variant():
    light = comparison_chart(["North", "South"], [120, 30])
    dark = comparison_chart(["North", "South"], [120, 30], mode="dark")
    assert _is_png_datauri(dark) and dark != light


def test_comparison_chart_grows_with_the_region_count():
    import io
    from matplotlib import image as mpimg
    def height(n):
        uri = comparison_chart([f"R{i}" for i in range(n)], list(range(n, 0, -1)))
        return mpimg.imread(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).shape[0]
    assert height(18) > height(3) * 2


def test_comparison_chart_handles_zero_and_single_region():
    assert _is_png_datauri(comparison_chart(["Only"], [0]))
    assert _is_png_datauri(comparison_chart(["A", "B"], [0, 5], percent=True, language="tr"))
