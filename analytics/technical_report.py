"""Teknik izleme raporu orkestratörü (LLM YOK — yalnızca kod-hesaplı bulgular).

Her indikatör için HAPI verisi çekilir, ulusal/bölgesel seri kurulur, istatistik
testleri + grafikler üretilir. Boş/hatalı dönen indikatör 'gaps'e eklenir ve atlanır.
findings_to_context, hesaplanmış sayıları LLM'e 'context' olarak verilecek metne
çevirir; LLM bunları yalnızca yorumlar, asla yeniden hesaplamaz.
"""
import logging
from dataclasses import dataclass

import requests

from analytics.charts import comparison_chart, correlation_chart, trend_chart
from analytics.datasets import national_series, regional_series
from analytics.hapi_client import HapiError, fetch_rows
from analytics.indicators import INDICATORS
from analytics.stat_tests import by_region, compare, correlate, trend
from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    heading: str
    stat_result: dict          # {"kind": "trend"|"compare"|"region", ...}
    chart: str | None          # base64 data-URI veya None
    findings_text: str         # LLM context'ine giren kod-hesaplı özet


@dataclass
class Findings:
    sections: list
    gaps: list
    indicators_covered: list


def compute_findings(iso3: str, date_from: str | None, date_to: str | None) -> Findings:
    settings = get_settings()
    min_pts = settings.TECHNICAL_REPORT_MIN_POINTS
    sections: list[ReportSection] = []
    gaps: list[str] = []
    covered: list[str] = []
    national_by_label: dict[str, tuple[list, list]] = {}   # korelasyon için (periods, values)

    for ind in INDICATORS:
        try:
            rows = fetch_rows(ind.endpoint, iso3,
                              extra_params=ind.query_params, admin_level=ind.admin_level)
        except (HapiError, requests.exceptions.RequestException) as exc:
            # HapiError: HAPI'nin kendi 4xx/retry-tükendi hatası. RequestException:
            # hapi_client ağ-seviyesi hatayı (ConnectionError/Timeout) HapiError'a
            # SARMIYOR — gerçek bir ağ kesintisinde ham fırlar. Sarmazsak tüm rapor
            # iptal olur; burada geniş tutup yalnızca bu indikatörü gaps'e düşürüyoruz.
            logger.warning("HAPI %s başarısız (%s): %s", ind.key, iso3, exc)
            gaps.append(f"{ind.label}: veri çekilemedi")
            continue

        # Fetch başarılıysa: seri kurma + tüm istatistik testleri + grafikler bu
        # try/except altında. Herhangi biri (örn. stats.kruskal'ın sabit-değerli
        # bölgelerde fırlattığı ValueError) patlarsa tüm rapor değil, yalnızca bu
        # indikatör gap'e düşer — diğer indikatörler işlenmeye devam eder.
        try:
            rows = _filter_period(rows, date_from, date_to)
            periods, values = national_series(rows, ind)
            if not values:
                gaps.append(f"{ind.label}: dönem içinde veri yok")
                continue
            covered.append(ind.key)
            national_by_label[ind.label] = (periods, values)

            # Trend
            tr = trend(values, indicator=ind.label, min_points=min_pts)
            if tr.direction == "insufficient_data":
                gaps.append(f"{ind.label}: trend için yetersiz veri (n={tr.n_points})")
            else:
                chart = trend_chart(periods, values, tr.slope, tr.intercept,
                                    title=f"{ind.label} — Trend", ylabel=ind.label)
                sections.append(ReportSection(
                    heading=f"{ind.label} — Trend Analizi",
                    stat_result={"kind": "trend", "indicator": ind.label,
                                 "direction": tr.direction, "slope": tr.slope,
                                 "p_value": tr.p_value, "pct_change": tr.pct_change,
                                 "n_points": tr.n_points, "ci_low": tr.ci_low,
                                 "ci_high": tr.ci_high},
                    chart=chart,
                    findings_text=_trend_text(tr),
                ))

            # Dönem karşılaştırması (ilk yarı vs ikinci yarı)
            # min_pts trend adımıyla tutarlı; min_pts >= 4 KALMALI, çünkü yarı-bölme
            # her iki gruba >= 2 nokta garantisi verir (t-testinin grup-başı >= 2 tabanı).
            if len(values) >= min_pts:
                mid = len(values) // 2
                cmp = compare(values[:mid], values[mid:], indicator=ind.label,
                              period_a=f"{periods[0]}–{periods[mid-1]}",
                              period_b=f"{periods[mid]}–{periods[-1]}")
                if cmp.note != "insufficient_data":
                    sections.append(ReportSection(
                        heading=f"{ind.label} — Dönem Karşılaştırması",
                        stat_result={"kind": "compare", "indicator": ind.label,
                                     "pct_change": cmp.pct_change, "p_value": cmp.p_value,
                                     "significant": cmp.significant,
                                     "period_a": cmp.period_a, "period_b": cmp.period_b},
                        chart=None,
                        findings_text=_compare_text(cmp),
                    ))

            # Bölgeler-arası (admin-1)
            reg = regional_series(rows, ind)
            if len(reg) >= 2:
                rr = by_region(reg, indicator=ind.label, period=f"{periods[0]}–{periods[-1]}")
                labels = [r for r, _ in rr.ranking]
                vals = [v for _, v in rr.ranking]
                chart = comparison_chart(labels, vals,
                                         title=f"{ind.label} — Bölge Karşılaştırması",
                                         ylabel=ind.label)
                sections.append(ReportSection(
                    heading=f"{ind.label} — Bölgesel Analiz",
                    stat_result={"kind": "region", "indicator": ind.label,
                                 "ranking": rr.ranking, "p_value": rr.p_value,
                                 "significant": rr.significant},
                    chart=chart,
                    findings_text=_region_text(rr),
                ))
        except Exception as exc:
            logger.warning("%s indikatörü analiz hatası (%s): %s", ind.key, iso3, exc)
            gaps.append(f"{ind.label}: analiz hatası")
            continue

    # İndikatörler-arası korelasyon: ortak dönemi olan indikatör çiftleri.
    labels = list(national_by_label.keys())
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            pa, va = national_by_label[labels[i]]
            pb, vb = national_by_label[labels[j]]
            xa, yb = _align_on_period(pa, va, pb, vb)
            if len(xa) < 3:
                continue
            cor = correlate(xa, yb, indicator_x=labels[i], indicator_y=labels[j])
            if cor.note == "insufficient_data":
                continue
            chart = correlation_chart(xa, yb, xlabel=labels[i], ylabel=labels[j],
                                      title=f"{labels[i]} ↔ {labels[j]}")
            sections.append(ReportSection(
                heading=f"Korelasyon — {labels[i]} ↔ {labels[j]}",
                stat_result={"kind": "correlation", "indicator_x": labels[i],
                             "indicator_y": labels[j], "coefficient": cor.coefficient,
                             "p_value": cor.p_value, "significant": cor.significant,
                             "method": cor.method, "n_points": cor.n_points},
                chart=chart,
                findings_text=_correlation_text(cor),
            ))

    return Findings(sections=sections, gaps=gaps, indicators_covered=covered)


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
    return "n/a" if p is None else f"{p:.3f}"


def _trend_text(tr) -> str:
    pct = "n/a" if tr.pct_change is None else f"%{tr.pct_change:.1f}"
    return (f"{tr.indicator}: yön={tr.direction}, eğim={tr.slope:.2f}/dönem, "
            f"p={_fmt_p(tr.p_value)} (α=0.05), toplam değişim={pct}, n={tr.n_points}.")


def _compare_text(cmp) -> str:
    pct = "n/a" if cmp.pct_change is None else f"%{cmp.pct_change:.1f}"
    sig = "anlamlı" if cmp.significant else "anlamlı değil"
    return (f"{cmp.indicator}: {cmp.period_a} → {cmp.period_b}, değişim={pct}, "
            f"p={_fmt_p(cmp.p_value)} ({sig}, α=0.05).")


def _region_text(rr) -> str:
    top = ", ".join(f"{name} ({val:.0f})" for name, val in rr.ranking[:3])
    sig = "anlamlı" if rr.significant else "anlamlı değil"
    return (f"{rr.indicator}: en yüksek bölgeler — {top}; bölgeler-arası fark "
            f"p={_fmt_p(rr.p_value)} ({sig}, α=0.05).")


def _correlation_text(cor) -> str:
    sig = "anlamlı" if cor.significant else "anlamlı değil"
    coef = "n/a" if cor.coefficient is None else f"{cor.coefficient:.2f}"
    return (f"{cor.indicator_x} ↔ {cor.indicator_y}: {cor.method} r={coef}, "
            f"p={_fmt_p(cor.p_value)} ({sig}, α=0.05, n={cor.n_points}).")


def findings_to_context(findings: Findings) -> str:
    # Her bölümün başlığı '## ' satırı olarak VERBATIM (kod-üretimli, s.heading) taşınır.
    # Render tarafı (report_pdf.py / reportImages.js) grafiği bu başlığa göre LLM çıktısındaki
    # '## ' başlığıyla eşleştirir — LLM başlığı burada göremezse kendi başlığını uydurur ve
    # grafik hiçbir zaman eşleşmez (bkz. FIX I1). Bu yüzden başlık LLM'e aynen verilir; prompt
    # bunu değiştirmeden kopyalamasını zorunlu kılar.
    lines = ["COMPUTED STATISTICAL FINDINGS (do not recompute — narrate only):", ""]
    for s in findings.sections:
        lines.append(f"## {s.heading}")
        lines.append(s.findings_text)
        lines.append("")
    if findings.gaps:
        lines.append("DATA GAPS:")
        for g in findings.gaps:
            lines.append(f"- {g}")
    return "\n".join(lines)


def assemble_section_images(findings: Findings) -> list[dict]:
    return [{"heading": s.heading, "image": s.chart}
            for s in findings.sections if s.chart]
