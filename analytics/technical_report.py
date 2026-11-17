"""Teknik izleme raporu orkestratörü (LLM YOK — yalnızca kod-hesaplı bulgular).

Her indikatör için HAPI verisi çekilir, ulusal/bölgesel seri kurulur, istatistik
testleri + grafikler üretilir. Boş/hatalı dönen indikatör 'gaps'e eklenir ve atlanır.
findings_to_context, hesaplanmış sayıları LLM'e 'context' olarak verilecek metne
çevirir; LLM bunları yalnızca yorumlar, asla yeniden hesaplamaz.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import date

import requests

from analytics.charts import comparison_chart, correlation_chart, trend_chart
from analytics.datasets import consistent_snapshots, ipc_coverage_note, national_series, regional_series
from analytics.hapi_client import HapiError, fetch_rows
from analytics.indicators import INDICATORS
from analytics.stat_tests import ALPHA, CORRELATION_MIN_POINTS, by_region, correlate, holm, trend
from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    heading: str
    stat_result: dict          # {"kind": "trend"|"region"|"correlation", ..., "p_adjusted", "significant"}
    chart: str | None          # base64 data-URI veya None
    findings_text: str         # LLM context'ine giren kod-hesaplı özet
    chart_dark: str | None = None   # the same chart drawn for the dark theme


@dataclass
class Findings:
    sections: list
    gaps: list
    indicators_covered: list
    date_from: str | None = None      # the period actually analysed
    date_to: str | None = None
    default_years: int | None = None  # set when no period was chosen (the last N years)
    notes: list = field(default_factory=list)   # what was left out of a series, and why


# Section headings are copied verbatim by the model and matched back to their charts,
# so they are written in the report language here, in code.
_HEADINGS = {
    "tr": {"trend": "{name} — Trend Analizi", "region": "{name} — Bölgesel Analiz",
           "correlation": "Korelasyon — {x} ↔ {y}"},
    "en": {"trend": "{name} — Trend Analysis", "region": "{name} — Regional Analysis",
           "correlation": "Correlation — {x} ↔ {y}"},
}


def compute_findings(iso3: str, date_from: str | None, date_to: str | None,
                     language: str = "tr") -> Findings:
    """*language* ("tr" or "en") names the indicators, section headings and chart
    text; the statistics do not depend on it."""
    settings = get_settings()
    headings = _HEADINGS.get(language, _HEADINGS["en"])
    min_pts = settings.TECHNICAL_REPORT_MIN_POINTS
    sections: list[ReportSection] = []
    gaps: list[str] = []
    covered: list[str] = []
    notes: list[str] = []
    national_by_label: dict[str, tuple[list, list]] = {}   # korelasyon için (periods, values)
    percent_by_label: dict[str, bool] = {}                 # share indicators (IPC %) → '%' ticks
    source_by_label: dict[str, str] = {}                   # credit, for the chart's source line
    # Dönem: seçilmediyse son N yıl; bitiş en geç bugün (HAPI gelecek yılların plan
    # kayıtlarını da döndürür — son nokta olarak sahte bir düşüş üretiyordu).
    today = date.today()
    default_years = None if date_from else settings.TECHNICAL_REPORT_DEFAULT_YEARS
    if default_years:
        date_from = _years_before(today, default_years).isoformat()
    date_to = min(date_to, today.isoformat()) if date_to else today.isoformat()

    for ind in INDICATORS:
        name = ind.name(language)
        try:
            rows = fetch_rows(ind.endpoint, iso3,
                              extra_params=ind.query_params, admin_level=ind.admin_level,
                              location_param=ind.location_param)
        except (HapiError, requests.exceptions.RequestException) as exc:
            # HapiError: HAPI'nin kendi 4xx/retry-tükendi hatası. RequestException:
            # hapi_client ağ-seviyesi hatayı (ConnectionError/Timeout) HapiError'a
            # SARMIYOR — gerçek bir ağ kesintisinde ham fırlar. Sarmazsak tüm rapor
            # iptal olur; burada geniş tutup yalnızca bu indikatörü gaps'e düşürüyoruz.
            logger.warning("HAPI %s başarısız (%s): %s", ind.key, iso3, exc)
            gaps.append(f"{name}: veri çekilemedi")
            continue

        # Fetch başarılıysa: seri kurma + tüm istatistik testleri + grafikler bu
        # try/except altında. Herhangi biri (örn. stats.kruskal'ın sabit-değerli
        # bölgelerde fırlattığı ValueError) patlarsa tüm rapor değil, yalnızca bu
        # indikatör gap'e düşer — diğer indikatörler işlenmeye devam eder.
        try:
            rows = _filter_period(rows, date_from, date_to)
            if ind.complete_periods_only:
                rows = _completed(rows, today)
            rows, note = consistent_snapshots(rows)
            coverage = ipc_coverage_note(rows)
            notes += [f"{name}: {n}" for n in (note, coverage) if n]
            periods, values = national_series(rows, ind)
            if not values:
                gaps.append(f"{name}: dönem içinde veri yok")
                continue
            covered.append(ind.key)
            national_by_label[name] = (periods, values)
            percent = ind.scale == 100
            percent_by_label[name] = percent
            source_by_label[name] = _credit(ind, periods[-1], language)
            source = _source_line([source_by_label[name]], language)

            # Trend (gerçek zaman ekseni: ilk dönemden beri yıl → eğim yıl başına)
            times = _years_since_first(periods)
            tr = trend(values, indicator=name, min_points=min_pts, times=times)
            if tr.direction == "insufficient_data":
                gaps.append(f"{name}: trend için yetersiz veri (n={tr.n_points})")
            else:
                chart, chart_dark = _both_modes(
                    trend_chart, periods, values, tr.slope, tr.intercept,
                    unit=_axis_unit(ind, language), times=times,
                    language=language, percent=percent, source=source)
                sections.append(ReportSection(
                    heading=headings["trend"].format(name=name),
                    stat_result={"kind": "trend", "indicator": name,
                                 "direction": tr.direction, "slope": tr.slope,
                                 "p_value": tr.p_value, "pct_change": tr.pct_change,
                                 "n_points": tr.n_points, "ci_low": tr.ci_low,
                                 "ci_high": tr.ci_high, "tau": tr.tau,
                                 "first_period": periods[0], "last_period": periods[-1],
                                 "unit": ind.unit},
                    chart=chart,
                    chart_dark=chart_dark,
                    findings_text="",
                ))

            # Bölgeler-arası (admin-1)
            reg = regional_series(rows, ind)
            if len(reg) >= 2:
                rr = by_region(reg, indicator=name, period=f"{periods[0]}–{periods[-1]}")
                labels = [r for r, _ in rr.ranking]
                vals = [v for _, v in rr.ranking]
                chart, chart_dark = _both_modes(
                    comparison_chart, labels, vals, language=language, percent=percent,
                    source=source)
                sections.append(ReportSection(
                    heading=headings["region"].format(name=name),
                    stat_result={"kind": "region", "indicator": name,
                                 "ranking": rr.ranking, "p_value": rr.p_value,
                                 "kruskal_h": rr.kruskal_h},
                    chart=chart,
                    chart_dark=chart_dark,
                    findings_text="",
                ))
        except Exception as exc:
            logger.warning("%s indikatörü analiz hatası (%s): %s", ind.key, iso3, exc)
            gaps.append(f"{name}: analiz hatası")
            continue

    # İndikatörler-arası korelasyon: ortak dönemi olan indikatör çiftleri.
    labels = list(national_by_label.keys())
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            pa, va = national_by_label[labels[i]]
            pb, vb = national_by_label[labels[j]]
            xa, yb = _align_on_period(pa, va, pb, vb)
            if len(xa) < CORRELATION_MIN_POINTS:
                continue
            cor = correlate(xa, yb, indicator_x=labels[i], indicator_y=labels[j])
            if cor.note == "insufficient_data":
                continue
            chart, chart_dark = _both_modes(
                correlation_chart, xa, yb, xlabel=labels[i], ylabel=labels[j],
                language=language,
                x_percent=percent_by_label[labels[i]],
                y_percent=percent_by_label[labels[j]],
                source=_source_line([source_by_label[labels[i]], source_by_label[labels[j]]],
                                    language))
            sections.append(ReportSection(
                heading=headings["correlation"].format(x=labels[i], y=labels[j]),
                stat_result={"kind": "correlation", "indicator_x": labels[i],
                             "indicator_y": labels[j], "coefficient": cor.coefficient,
                             "p_value": cor.p_value,
                             "method": cor.method, "n_points": cor.n_points},
                chart=chart,
                chart_dark=chart_dark,
                findings_text="",
            ))

    _adjust_and_describe(sections)
    return Findings(sections=sections, gaps=gaps, indicators_covered=covered,
                    date_from=date_from, date_to=date_to, default_years=default_years,
                    notes=notes)


_MONTH_NAMES = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
           "Eylül", "Ekim", "Kasım", "Aralık"],
}


def _credit(ind, last_period, language: str) -> str:
    """How a chart names the indicator's publisher: its required credit line (IOM DTM),
    dated to the month of the latest data shown, or else the short publisher name."""
    if not ind.credit:
        return ind.source
    months = _MONTH_NAMES.get(language, _MONTH_NAMES["en"])
    try:
        day = date.fromisoformat(str(last_period)[:10])
        month_year = f"{months[day.month - 1]} {day.year}"
    except ValueError:
        month_year = str(last_period)
    return ind.credit.format(month_year=month_year)


def _source_line(publishers: list[str], language: str) -> str:
    """'Source: IOM DTM · HDX HAPI' — the publishers (or their required credit lines,
    which contain commas, hence the semicolons), then the API we read them from."""
    names = list(dict.fromkeys(p for p in publishers if p))
    prefix = "Kaynak" if language == "tr" else "Source"
    return f"{prefix}: {'; '.join(names)} · HDX HAPI" if names else f"{prefix}: HDX HAPI"


def _axis_unit(ind, language: str) -> str:
    """What the value axis counts. Shares need none: their ticks read '45%'."""
    if ind.scale == 100:
        return ""
    if ind.key == "funding":
        return "USD"
    return "kişi" if language == "tr" else "people"


def _both_modes(draw, *args, **kwargs) -> tuple[str, str]:
    """The chart for the light theme (also used in the PDF) and for the dark theme."""
    return draw(*args, mode="light", **kwargs), draw(*args, mode="dark", **kwargs)


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:              # 29 February → 28 February
        return day.replace(year=day.year - years, day=28)


def _completed(rows: list[dict], today: date) -> list[dict]:
    """Rows whose reference period has ended (a row without an end date is kept)."""
    return [r for r in rows
            if not r.get("reference_period_end")
            or str(r["reference_period_end"])[:10] <= today.isoformat()]


def _adjust_and_describe(sections: list) -> None:
    """Holm-adjust every test of the report together (one family), decide
    significance in code from the adjusted p, and write each section's findings
    text — the model narrates the verdict, it never decides it."""
    adjusted = holm([s.stat_result.get("p_value") for s in sections])
    for s, p_adj in zip(sections, adjusted):
        s.stat_result["p_adjusted"] = p_adj
        s.stat_result["significant"] = p_adj is not None and p_adj < ALPHA
        s.findings_text = _TEXT[s.stat_result["kind"]](s.stat_result)


def _years_since_first(periods: list[str]) -> list[float]:
    """Each period's start as years since the first one (real spacing: a missing
    year leaves a gap instead of being squeezed out)."""
    days = [date.fromisoformat(str(p)[:10]) for p in periods]
    return [(d - days[0]).days / 365.25 for d in days]


def _align_on_period(periods_a, values_a, periods_b, values_b):
    """İki seriyi ortak dönemlerde hizala → (x, y) eşit uzunlukta, döneme göre sıralı."""
    map_a = dict(zip(periods_a, values_a))
    map_b = dict(zip(periods_b, values_b))
    common = sorted(set(map_a) & set(map_b))
    return [map_a[p] for p in common], [map_b[p] for p in common]


def _filter_period(rows: list[dict], date_from: str | None, date_to: str | None) -> list[dict]:
    """reference_period_start üzerinden istemci-tarafı dönem filtresi (ISO tarih
    karşılaştırması; HAPI sunucu-parametresi endpoint'e göre değiştiğinden savunmacı)."""
    if not date_from and not date_to:
        return rows
    out = []
    for r in rows:
        start = str(r.get("reference_period_start") or "")[:10]
        if not start:
            continue
        if date_from and start < date_from:
            continue
        if date_to and start > date_to:
            continue
        out.append(r)
    return out


def _fmt_p(p: float | None) -> str:
    """'p=0.012', 'p<0.001' or 'p=n/a' (the 'p' included, so '<' never follows '=')."""
    if p is None:
        return "p=n/a"
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def _verdict(r: dict) -> str:
    return (f"{_fmt_p(r['p_value'])}, Holm-adjusted {_fmt_p(r['p_adjusted'])} → "
            f"{'SIGNIFICANT' if r['significant'] else 'NOT SIGNIFICANT'} (α=0.05)")


def _plain(x: float) -> str:
    """A value as the model should repeat it: three significant digits for large
    magnitudes (931170.92 → 931000), one decimal from 10, two below. The report
    used to quote slopes and intervals to the cent ("-931,170.92 people a year")."""
    if x == 0 or not math.isfinite(x):
        return f"{x:g}"
    if abs(x) >= 1000:
        return f"{round(x, 2 - int(math.floor(math.log10(abs(x))))):.0f}"
    return f"{x:.1f}" if abs(x) >= 10 else f"{x:.2f}"


def _trend_text(r: dict) -> str:
    pct = "n/a" if r["pct_change"] is None else f"{r['pct_change']:+.1f}%"
    ci = ("95% CI: too few points" if r["ci_low"] is None
          else f"95% CI {_plain(r['ci_low'])} to {_plain(r['ci_high'])}")
    unit = f" {r['unit']}" if r.get("unit") else ""
    return (f"{r['indicator']}: direction={r['direction']}, Sen slope={_plain(r['slope'])}{unit} per year "
            f"({ci}), Kendall tau={r['tau']:.2f}, Mann-Kendall {_verdict(r)}, "
            f"relative change along the trend line {str(r['first_period'])[:10]} → {str(r['last_period'])[:10]}={pct}, "
            f"n={r['n_points']}.")


def _region_text(r: dict) -> str:
    top = ", ".join(f"{name} ({_plain(val)})" for name, val in r["ranking"][:3])
    h = "n/a" if r["kruskal_h"] is None else f"{r['kruskal_h']:.2f}"
    return (f"{r['indicator']}: highest regions — {top}; difference between regions "
            f"Kruskal-Wallis H={h}, {_verdict(r)}.")


def _correlation_text(r: dict) -> str:
    coef = "n/a" if r["coefficient"] is None else f"{r['coefficient']:.2f}"
    return (f"{r['indicator_x']} ↔ {r['indicator_y']}: {r['method']} r={coef}, "
            f"{_verdict(r)}, n={r['n_points']}.")


_TEXT = {"trend": _trend_text, "region": _region_text, "correlation": _correlation_text}


def findings_to_context(findings: Findings) -> str:
    # Her bölümün başlığı '## ' satırı olarak VERBATIM (kod-üretimli, s.heading) taşınır.
    # Render tarafı (report_pdf.py / reportImages.js) grafiği bu başlığa göre LLM çıktısındaki
    # '## ' başlığıyla eşleştirir — LLM başlığı burada göremezse kendi başlığını uydurur ve
    # grafik hiçbir zaman eşleşmez (bkz. FIX I1). Bu yüzden başlık LLM'e aynen verilir; prompt
    # bunu değiştirmeden kopyalamasını zorunlu kılar.
    lines = ["COMPUTED STATISTICAL FINDINGS (do not recompute — narrate only):", ""]
    if findings.date_from:
        chosen = (f" (no period was chosen: the last {findings.default_years} years)"
                  if findings.default_years else "")
        lines += [f"PERIOD ANALYSED: {findings.date_from} to {findings.date_to}{chosen}", ""]
    for s in findings.sections:
        lines.append(f"## {s.heading}")
        lines.append(s.findings_text)
        lines.append("")
    if findings.gaps:
        lines.append("DATA GAPS:")
        for g in findings.gaps:
            lines.append(f"- {g}")
        lines.append("")
    if findings.notes:
        lines.append("DATA NOTES:")
        lines += [f"- {n}" for n in findings.notes]
        lines.append("")
    tested = sum(1 for s in findings.sections if s.stat_result.get("p_value") is not None)
    lines += [
        "METHOD NOTES:",
        "- Trend: Mann-Kendall test; the slope is Sen's slope per year on the real dates of "
        "the periods; Kendall tau is the effect size.",
        "- Regions: Kruskal-Wallis test across admin-1 regions.",
        f"- Correlation: Pearson, only for indicator pairs with at least "
        f"{CORRELATION_MIN_POINTS} common periods.",
        f"- Multiple comparisons: Holm correction across all {tested} tests in this report; "
        "significance is decided on the Holm-adjusted p-value at α=0.05.",
        "- Limitation: the series are short; the tests assume independent observations and "
        "serial correlation between consecutive periods is not corrected for, so the results "
        "are indicative.",
    ]
    return "\n".join(lines)


def assemble_section_images(findings: Findings) -> list[dict]:
    """`image` is the light chart (the PDF uses it); `image_dark` the dark-theme one."""
    out = []
    for s in findings.sections:
        if not s.chart:
            continue
        item = {"heading": s.heading, "image": s.chart}
        if s.chart_dark:
            item["image_dark"] = s.chart_dark
        out.append(item)
    return out
