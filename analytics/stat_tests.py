"""Teknik izleme raporu için saf istatistik fonksiyonları.

Girdi düz list/dict, çıktı frozen dataclass. Network/dış durum yok → sentetik
veriyle tam test edilebilir. Yetersiz veride (min_points altı, sıfır varyans,
n<=2, NaN) inferential test ÇALIŞTIRILMAZ; sonuç 'insufficient_data' işaretlenir
ve p-değeri asla uydurulmaz.
"""
import logging
import math
import statistics
from dataclasses import dataclass

from scipy import stats
import pymannkendall as mk

logger = logging.getLogger(__name__)

ALPHA = 0.05
# Short trending series correlate spuriously (both just move with time); below this
# many common periods no correlation test runs.
CORRELATION_MIN_POINTS = 8


@dataclass(frozen=True)
class TrendResult:
    indicator: str
    n_points: int
    slope: float | None       # Sen eğimi, zaman birimi başına (times yıl ise yıl başına)
    p_value: float | None     # Mann-Kendall
    direction: str            # increasing | decreasing | no trend | insufficient_data
    pct_change: float | None  # Sen doğrusu boyunca ilk → son dönem (işareti eğimle aynı)
    ci_low: float | None      # Sen eğiminin %95 güven aralığı; az noktada tanımsız → None
    ci_high: float | None
    intercept: float | None   # Sen doğrusunun t=0'daki değeri — grafikte trend çizgisi
    tau: float | None = None  # Kendall τ (etki büyüklüğü, -1..1)


@dataclass(frozen=True)
class RegionResult:
    indicator: str
    period: str
    ranking: list             # list[tuple[str, float]] mean değere göre azalan
    kruskal_h: float | None
    p_value: float | None
    significant: bool


@dataclass(frozen=True)
class CorrelationResult:
    indicator_x: str
    indicator_y: str
    n_points: int
    method: str               # pearson | spearman
    coefficient: float | None
    p_value: float | None
    significant: bool
    note: str


def _clean(values) -> list[float]:
    """NaN/None düşürülmüş float listesi."""
    out = []
    for v in values or []:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(f):
            out.append(f)
    return out


def _sen_slope(times: list[float], values: list[float], var_s: float):
    """Sen eğimi (ikili eğimlerin medyanı) + %95 güven aralığı (Gilbert 1987, Mann-Kendall
    S varyansından). Gerçek zaman ekseninde çalışır, düzensiz aralıkları doğru ölçekler.
    Az noktada güven aralığı tanımsızdır (C ikili sayısını aşar) → (slope, None, None)."""
    n = len(values)
    slopes = sorted((values[j] - values[i]) / (times[j] - times[i])
                    for i in range(n) for j in range(i + 1, n) if times[j] != times[i])
    m = len(slopes)
    mid = m // 2
    slope = slopes[mid] if m % 2 else (slopes[mid - 1] + slopes[mid]) / 2
    c = stats.norm.ppf(0.975) * math.sqrt(var_s)
    # Alt sınır M1'inci, üst sınır (M2+1)'inci en küçük ikili eğim (1-tabanlı, yuvarlanmış).
    lower, upper = round((m - c) / 2), round((m + c) / 2)
    if lower < 1 or upper > m - 1:
        return slope, None, None
    return slope, slopes[lower - 1], slopes[upper]


def trend(values, indicator: str, min_points: int = 4, times=None) -> TrendResult:
    """Mann-Kendall trend testi + Sen eğimi. *times*: her gözlemin zamanı (ör. ilk
    dönemden beri yıl); verilmezse gözlemler eşit aralıklı sayılır (0, 1, 2, ...).
    Bağımsız gözlem varsayar — otokorelasyon düzeltilmez (kısa serilerde düzeltme
    güvenilmez); rapor bunu sınırlama olarak belirtir."""
    pairs = [(t, f) for t, f in zip(times if times is not None else range(len(values or [])), values or [])
             if f is not None and not (isinstance(f, float) and math.isnan(f))]
    t = [float(x) for x, _ in pairs]
    v = _clean([y for _, y in pairs])
    n = len(v)
    # Yetersiz veri / sıfır varyans → test yok.
    if n < min_points or len(set(v)) < 2:
        return TrendResult(indicator, n, None, None, "insufficient_data", None, None, None, None)
    mk_res = mk.original_test(v)
    slope, ci_low, ci_high = _sen_slope(t, v, mk_res.var_s)
    intercept = statistics.median(y - slope * x for x, y in zip(t, v))
    # Yön, Tau işaretinden (yönü tanımlar); p-değeri anlamlılığı ayrıca taşır.
    # (mk_res.trend, küçük n'de anlamlılık eşiğine takılıp gerçek bir monoton
    # artışı bile "no trend" işaretleyebiliyor — yön ile anlamlılığı ayırıyoruz.)
    if mk_res.Tau > 0:
        direction = "increasing"
    elif mk_res.Tau < 0:
        direction = "decreasing"
    else:
        direction = "no trend"
    # Değişim, uç noktalar yerine trend doğrusu üzerinden: zirveden önce başlayıp düşen
    # bir seri 'azalış' trendinin yanında '+%21' yazıyordu (Sudan IDP, canlı kontrol).
    line_start, line_end = intercept + slope * t[0], intercept + slope * t[-1]
    pct = (line_end - line_start) / line_start * 100.0 if line_start > 0 else None
    return TrendResult(
        indicator=indicator, n_points=n, slope=float(slope),
        p_value=float(mk_res.p), direction=direction, pct_change=pct,
        ci_low=ci_low, ci_high=ci_high, intercept=float(intercept), tau=float(mk_res.Tau),
    )


def by_region(region_series: dict, indicator: str, period: str) -> RegionResult:
    cleaned = {r: _clean(vs) for r, vs in (region_series or {}).items()}
    cleaned = {r: vs for r, vs in cleaned.items() if vs}
    ranking = sorted(
        ((r, sum(vs) / len(vs)) for r, vs in cleaned.items()),
        key=lambda kv: kv[1], reverse=True,
    )
    testable = [vs for vs in cleaned.values() if len(vs) >= 2]
    if len(testable) < 2:
        return RegionResult(indicator, period, ranking, None, None, False)
    h, p = stats.kruskal(*testable)
    return RegionResult(indicator, period, ranking, float(h), float(p), bool(p < ALPHA))


def correlate(x, y, indicator_x: str, indicator_y: str, method: str = "pearson") -> CorrelationResult:
    xs, ys = _clean(x), _clean(y)
    n = min(len(xs), len(ys))
    xs, ys = xs[:n], ys[:n]
    if n < CORRELATION_MIN_POINTS or len(set(xs)) < 2 or len(set(ys)) < 2:
        return CorrelationResult(indicator_x, indicator_y, n, method, None, None, False,
                                 "insufficient_data")
    if method == "spearman":
        res = stats.spearmanr(xs, ys)
        coef, p = float(res.statistic), float(res.pvalue)
    else:
        res = stats.pearsonr(xs, ys)
        coef, p = float(res.statistic), float(res.pvalue)
    return CorrelationResult(
        indicator_x=indicator_x, indicator_y=indicator_y, n_points=n, method=method,
        coefficient=coef, p_value=p, significant=bool(p < ALPHA), note="",
    )


def holm(p_values: list) -> list:
    """Holm-Bonferroni düzeltmesi: bir rapordaki tüm testler tek aile. None (test
    yapılmadı) olduğu gibi kalır; düzeltilmiş p'ler orijinal sırada, en fazla 1."""
    indexed = sorted((p, i) for i, p in enumerate(p_values) if p is not None)
    m = len(indexed)
    out = list(p_values)
    running = 0.0
    for rank, (p, i) in enumerate(indexed):
        running = max(running, min(1.0, (m - rank) * p))
        out[i] = running
    return out
