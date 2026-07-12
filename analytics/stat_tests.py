"""Teknik izleme raporu için saf istatistik fonksiyonları.

Girdi düz list/dict, çıktı frozen dataclass. Network/dış durum yok → sentetik
veriyle tam test edilebilir. Yetersiz veride (min_points altı, sıfır varyans,
n<=2, NaN) inferential test ÇALIŞTIRILMAZ; sonuç 'insufficient_data' işaretlenir
ve p-değeri asla uydurulmaz.
"""
import logging
import math
from dataclasses import dataclass

from scipy import stats
import pymannkendall as mk

logger = logging.getLogger(__name__)

ALPHA = 0.05


@dataclass(frozen=True)
class TrendResult:
    indicator: str
    n_points: int
    slope: float | None
    p_value: float | None
    direction: str            # increasing | decreasing | no trend | insufficient_data
    pct_change: float | None
    ci_low: float | None
    ci_high: float | None
    intercept: float | None   # OLS intercept (linregress) — grafikte trend çizgisinin başlangıcı


@dataclass(frozen=True)
class CompareResult:
    indicator: str
    period_a: str
    period_b: str
    pct_change: float | None
    t_statistic: float | None
    p_value: float | None
    significant: bool
    note: str                 # "" | insufficient_data


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


def trend(values, indicator: str, min_points: int = 4) -> TrendResult:
    v = _clean(values)
    n = len(v)
    # Yetersiz veri / sıfır varyans → test yok.
    if n < min_points or len(set(v)) < 2:
        return TrendResult(indicator, n, None, None, "insufficient_data", None, None, None, None)
    x = list(range(n))
    lr = stats.linregress(x, v)
    tcrit = stats.t.ppf(0.975, n - 2)
    half = tcrit * lr.stderr
    mk_res = mk.original_test(v)
    # Yön, Tau işaretinden (yönü tanımlar); p-değeri anlamlılığı ayrıca taşır.
    # (mk_res.trend, küçük n'de anlamlılık eşiğine takılıp gerçek bir monoton
    # artışı bile "no trend" işaretleyebiliyor — yön ile anlamlılığı ayırıyoruz.)
    if mk_res.Tau > 0:
        direction = "increasing"
    elif mk_res.Tau < 0:
        direction = "decreasing"
    else:
        direction = "no trend"
    pct = ((v[-1] - v[0]) / v[0] * 100.0) if v[0] != 0 else None
    return TrendResult(
        indicator=indicator, n_points=n, slope=float(lr.slope),
        p_value=float(mk_res.p), direction=direction, pct_change=pct,
        ci_low=float(lr.slope - half), ci_high=float(lr.slope + half),
        intercept=float(lr.intercept),
    )


def compare(before, after, indicator: str, period_a: str, period_b: str) -> CompareResult:
    a, b = _clean(before), _clean(after)
    if len(a) < 2 or len(b) < 2 or len(set(a)) < 2 and len(set(b)) < 2:
        pct = None
        if a and b and sum(a) != 0:
            pct = (sum(b) / len(b) - sum(a) / len(a)) / (sum(a) / len(a)) * 100.0
        return CompareResult(indicator, period_a, period_b, pct, None, None, False,
                             "insufficient_data")
    t_stat, p = stats.ttest_ind(b, a, equal_var=False)
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    pct = ((mean_b - mean_a) / mean_a * 100.0) if mean_a != 0 else None
    return CompareResult(
        indicator=indicator, period_a=period_a, period_b=period_b, pct_change=pct,
        t_statistic=float(t_stat), p_value=float(p), significant=bool(p < ALPHA), note="",
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
    if n < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
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
