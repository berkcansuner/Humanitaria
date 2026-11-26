"""Teknik izleme raporu orkestratörü (LLM YOK — yalnızca kod-hesaplı bulgular).

Her indikatör için HAPI verisi çekilir, ulusal/bölgesel seri kurulur, istatistik
testleri + grafikler üretilir. Boş/hatalı dönen indikatör 'gaps'e eklenir ve atlanır.
Raporun metnini analytics.report_text yazar. findings_to_context bulguları düz metin
olarak okur; artık hiçbir modele gitmez, testler bulguları onunla denetler.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import requests

from analytics.charts import comparison_chart, correlation_chart, trend_chart
from analytics.datasets import (
    competing_totals, competing_totals_note, consistent_snapshots, ipc_coverage,
    ipc_coverage_note, national_series, regional_series, snapshot_selection, sub_sector_lines,
)
from analytics.hapi_client import HapiError, fetch_rows, resource_metadata
from analytics.indicators import indicators_for
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
    # Trends taken over a longer look-back than the chosen period (too few points in it):
    # {"indicator", "chosen_points", "date_from", "date_to"} — the window the trend covers.
    look_backs: list = field(default_factory=list)
    # Indicators whose HAPI request failed (an outage, not an absence of data).
    failed: list = field(default_factory=list)
    # One entry per indicator with data: what the report's source list is built from
    # ({"key", "title", "source", "first_period", "last_period", "resource_hdx_id"}).
    data_sources: list = field(default_factory=list)
    # A sector report's own figures (its people-in-need series), each with the short caveat
    # a summary sentence must carry: what the Executive Summary opens with.
    headline: list = field(default_factory=list)
    # The same gaps, notes and headline figures as data, for the report's own text in its
    # language (analytics.report_text); the strings above are the model's English context.
    gap_items: list = field(default_factory=list)       # {"name", "code", "n"}
    note_items: list = field(default_factory=list)      # {"name", "window", "kind", …}
    headline_items: list = field(default_factory=list)


# Section headings are copied verbatim by the model and matched back to their charts,
# so they are written in the report language here, in code.
_HEADINGS = {
    "tr": {"trend": "{name} — Eğilim Analizi", "region": "{name} — Bölgesel Analiz",
           "correlation": "Korelasyon — {x} ↔ {y}", "snapshot": "{name} — Son Değerler"},
    "en": {"trend": "{name} — Trend Analysis", "region": "{name} — Regional Analysis",
           "correlation": "Correlation — {x} ↔ {y}", "snapshot": "{name} — Latest Values"},
}


def _today() -> date:
    """Today in UTC: the day the period is capped at, and the retrieval day."""
    return datetime.now(timezone.utc).date()


def compute_findings(iso3: str, date_from: str | None, date_to: str | None,
                     language: str = "tr", theme: str | None = None) -> Findings:
    """*language* ("tr" or "en") names the indicators, section headings and chart
    text; the statistics do not depend on it. *theme*: the report's sector — only its
    indicators are analysed (None = all sectors, the six overview indicators)."""
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
    today = _today()
    default_years = None if date_from else settings.TECHNICAL_REPORT_DEFAULT_YEARS
    if default_years:
        date_from = _years_before(today, default_years).isoformat()
    # The form sends the user's local date: up to one day ahead of the server's (UTC)
    # today it is a real "today" east of UTC and is kept; anything later is capped.
    latest_today = (today + timedelta(days=1)).isoformat()
    date_to = (date_to if date_to and date_to <= latest_today
               else min(date_to, today.isoformat()) if date_to else today.isoformat())
    look_back_from = _years_before(date.fromisoformat(date_to),
                                   settings.TECHNICAL_REPORT_DEFAULT_YEARS).isoformat()
    look_backs: list[dict] = []
    failed: list[str] = []
    used: list[dict] = []
    headline: list[str] = []
    gap_items: list[dict] = []
    note_items: list[dict] = []
    headline_items: list[dict] = []

    for ind in indicators_for(theme):
        name = ind.name(language)
        sections_before = len(sections)
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
            gaps.append(f"{name}: could not be retrieved from HDX HAPI")
            gap_items.append({"name": name, "code": "not_retrieved"})
            failed.append(ind.key)
            continue

        # Fetch başarılıysa: seri kurma + tüm istatistik testleri + grafikler bu
        # try/except altında. Herhangi biri (örn. stats.kruskal'ın sabit-değerli
        # bölgelerde fırlattığı ValueError) patlarsa tüm rapor değil, yalnızca bu
        # indikatör gap'e düşer — diğer indikatörler işlenmeye devam eder.
        try:
            all_rows = rows
            rows, series_notes, series_items, periods, values = _series_detail(
                all_rows, ind, date_from, date_to, today)
            # Too few points in the chosen period for a trend: the trend looks back over
            # the default window ending at the chosen end (most HAPI series are yearly or
            # half-yearly, so a one-year period held one observation). Only the trend
            # uses it; the regional ranking and the correlations stay on the chosen period.
            look_back = None
            t_periods, t_values = periods, values
            if len(values) < min_pts and look_back_from < date_from:
                _, lb_notes, lb_items, lb_periods, lb_values = _series_detail(
                    all_rows, ind, look_back_from, date_to, today)
                if len(lb_values) > len(values):
                    look_back = {"date_from": look_back_from, "date_to": date_to,
                                 "chosen_points": len(values)}
                    t_periods, t_values = lb_periods, lb_values
            name, line_notes, not_comparable, latest_caveat = _plan_line(
                ind, all_rows, t_periods, t_values, language)
            plan = _plan_line_detail(ind, all_rows, t_periods, t_values)
            # The look-back's notes only when a section will show its values (a series
            # too short for a trend under "All sectors" is a gap line, its values unshown).
            shows_look_back = look_back and (
                theme is not None or not_comparable
                or (len(t_values) >= min_pts and len(set(t_values)) > 1))
            if shows_look_back and lb_notes != series_notes:
                # Each window's notes, named: the regional ranking stays on the chosen
                # period, the trend covers the look-back.
                notes += [f"{name} (chosen period): {n}" for n in series_notes]
                notes += [f"{name} (look-back window): {n}" for n in lb_notes]
                note_items += [{"name": name, "window": "chosen", **i} for i in series_items]
                note_items += [{"name": name, "window": "look_back", **i} for i in lb_items]
            else:
                notes += [f"{name}: {n}" for n in series_notes]
                note_items += [{"name": name, "window": None, **i} for i in series_items]
            notes += line_notes
            note_items += [{"name": name, "window": None, **i} for i in plan["notes"]]
            if not t_values:
                gaps.append(f"{name}: no data in the period")
                gap_items.append({"name": name, "code": "no_data"})
                continue
            covered.append(ind.key)
            if look_back is None:
                national_by_label[name] = (periods, values)
            percent = ind.scale == 100
            percent_by_label[name] = percent
            source_by_label[name] = _credit(ind, t_periods[-1], language)
            source = _source_line([source_by_label[name]], language)
            latest = str(t_periods[-1])[:10]
            used.append({"key": ind.key, "title": name, "source": source_by_label[name],
                         "first_period": str(t_periods[0])[:10], "last_period": latest,
                         "resource_hdx_id": next(
                             (r["resource_hdx_id"] for r in all_rows if r.get("resource_hdx_id")
                              and str(r.get("reference_period_start"))[:10] == latest), None)})

            # Trend (gerçek zaman ekseni: ilk dönemden beri yıl → eğim yıl başına)
            times = _years_since_first(t_periods)
            tr = trend(t_values, indicator=name, min_points=min_pts, times=times)
            if tr.direction == "insufficient_data":
                gaps.append(f"{name}: too few observations for a trend test (n={tr.n_points})")
                gap_items.append({"name": name, "code": "too_few", "n": tr.n_points})
            elif not_comparable:
                # Years that are different plan lines: no trend is tested across them.
                gaps.append(f"{name}: years not comparable, so no trend was tested")
                gap_items.append({"name": name, "code": "not_comparable"})
            if (tr.direction == "insufficient_data" and theme is not None) or not_comparable:
                # The values are still the sector's figures: reported as they are, untested.
                # ("All sectors" keeps such a series as a gap only, as it always did.)
                chart, chart_dark = _both_modes(
                    trend_chart, t_periods, t_values, None, None,
                    unit=_axis_unit(ind, language), times=times,
                    language=language, percent=percent, source=source,
                    connect=not not_comparable)
                sections.append(ReportSection(
                    heading=headings["snapshot"].format(name=name),
                    stat_result={"kind": "snapshot", "indicator": name, "p_value": None,
                                 "periods": t_periods, "values": t_values,
                                 "value_unit": _value_unit(ind), "min_points": min_pts,
                                 "look_back": look_back, "chosen_from": date_from,
                                 "not_comparable": not_comparable,
                                 "not_comparable_years": plan["years"] if not_comparable else None,
                                 "sector_en": ind.sector_en, "sector_tr": ind.sector_tr,
                                 "resolution": ind.resolution, "exact": bool(line_notes)},
                    chart=chart,
                    chart_dark=chart_dark,
                    findings_text="",
                ))
            elif tr.direction != "insufficient_data":
                if look_back:
                    look_backs.append({"indicator": name, **look_back})
                chart, chart_dark = _both_modes(
                    trend_chart, t_periods, t_values, tr.slope, tr.intercept,
                    unit=_axis_unit(ind, language), times=times,
                    language=language, percent=percent, source=source)
                sections.append(ReportSection(
                    heading=headings["trend"].format(name=name),
                    stat_result={"kind": "trend", "indicator": name,
                                 "direction": tr.direction, "slope": tr.slope,
                                 "p_value": tr.p_value, "pct_change": tr.pct_change,
                                 "n_points": tr.n_points, "ci_low": tr.ci_low,
                                 "ci_high": tr.ci_high, "tau": tr.tau,
                                 "first_period": t_periods[0], "last_period": t_periods[-1],
                                 "unit": ind.unit, "look_back": look_back,
                                 "chosen_from": date_from,
                                 "latest_value": t_values[-1], "latest_period": t_periods[-1],
                                 "first_value": t_values[0],
                                 "periods": t_periods, "values": t_values,
                                 # A share changes in percentage points along the line,
                                 # never as a relative percent of a percent.
                                 "line_change": (tr.slope * times[-1]
                                                 if ind.unit == "percentage points" else None),
                                 "value_unit": _value_unit(ind), "resolution": ind.resolution},
                    chart=chart,
                    chart_dark=chart_dark,
                    findings_text="",
                ))

            # Bölgeler-arası (admin-1)
            reg = regional_series(rows, ind) if values else {}
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
                                 "kruskal_h": rr.kruskal_h,
                                 "max_obs": max(len(v) for v in reg.values()),
                                 "first_period": periods[0], "last_period": periods[-1],
                                 "value_unit": _value_unit(ind), "resolution": ind.resolution},
                    chart=chart,
                    chart_dark=chart_dark,
                    findings_text="",
                ))
        except Exception as exc:
            logger.warning("%s indikatörü analiz hatası (%s): %s", ind.key, iso3, exc)
            gaps.append(f"{name}: analysis error")
            gap_items.append({"name": name, "code": "analysis_error"})
            used[:] = [u for u in used if u["key"] != ind.key]   # not in the report: no source
            continue
        if len(sections) == sections_before:
            # Only a gap line ("All sectors" keeps a short series as one): not a source of
            # anything the report shows.
            used[:] = [u for u in used if u["key"] != ind.key]
        elif theme is not None and ind.query_params.get("sector_code"):
            # The sector's own figure, for the Executive Summary to open with.
            caveats = [c for c in (
                "earlier years are reported on a different basis and are not comparable"
                if not_comparable else None, latest_caveat) if c]
            before = ", before the chosen period" if look_back and not look_back["chosen_points"] else ""
            figure = (f"{_full(t_values[-1])} {_value_unit(ind)}" if line_notes
                      else _amount(t_values[-1], _value_unit(ind)))
            headline.append(f"{name}: {figure} "
                            f"({_when(t_periods[-1], ind.resolution)}{before})"
                            + (f"; {'; '.join(caveats)}" if caveats else "") + ".")
            headline_items.append({
                "name": name, "value": t_values[-1], "unit": _value_unit(ind),
                "period": t_periods[-1], "resolution": ind.resolution, "exact": bool(line_notes),
                "before": bool(before), "not_comparable": bool(not_comparable),
                "caveat": plan["caveat"], "sector_en": ind.sector_en, "sector_tr": ind.sector_tr})

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
                    notes=notes, look_backs=look_backs, failed=failed, data_sources=used,
                    headline=headline, gap_items=gap_items, note_items=note_items,
                    headline_items=headline_items)


def _full(value: float) -> str:
    """A figure in full with thousands separators (14,173,291): two plan lines must never
    print as the same rounded number."""
    return f"{int(round(value)):,}"


def _plan_line(ind, rows: list[dict], periods: list, values: list,
               language: str) -> tuple[str, list[str], str | None, str | None]:
    """The indicator's name, a note for every period whose plan reports the sector in
    separate lines (HAPI returns the sub-sectors beside it: PRO-CPN, PRO-GBV …), and,
    when the series' years are not all the plan's only figure, why they are not
    comparable.

    HAPI's figure for the parent code is then one of the plan's lines, and HAPI's rows
    cannot say which: Haiti 2024's 250,000 is the migrants line, Haiti 2025's 466,589 the
    general line, Congo 2025's 7,870,319 the overall figure. So only what the rows show is
    said: below one of its sub-lines, the figure is not the overall figure; otherwise it
    may be one of the lines. The figure is never called the general line, nothing is said
    about an overall figure the data does not hold, and the lines are never added up."""
    name = ind.name(language)
    lines = sub_sector_lines(rows, ind)
    by_period = {str(p)[:10]: v for p, v in zip(periods, values)}
    lines = {p: subs for p, subs in lines.items() if p in by_period}
    if not lines:
        return name, [], None, None

    def below(period):
        return any(v > by_period[period] for _, v in lines.get(period, []))

    sector = ind.sector_en or "the sector"
    notes = []
    for period, subs in lines.items():
        listed = ", ".join(f"{n} {_full(v)}" for n, v in subs)
        figure = _full(by_period[period])
        if below(period):
            what = (f"this figure ({figure}) is below one of the plan's {sector} lines, so it is "
                    f"not the plan's overall {sector} figure; HDX HAPI does not say which of the "
                    f"plan's lines it is")
        else:
            # It equals none of the listed lines, so it is not said to be one of them.
            what = (f"this figure ({figure}) may be another of the plan's {sector} lines (not "
                    f"listed in HDX HAPI) rather than its overall {sector} figure")
        notes.append(f"{name}, {period[:4]}: the plan reports {sector} in separate lines "
                     f"({listed}); {what}; this report does not add the lines up, because people "
                     f"can be counted in more than one.")
    latest = str(periods[-1])[:10]
    caveat = None
    if latest in lines:
        caveat = (f"it is not the plan's overall {sector} figure" if below(latest)
                  else f"it may not be the plan's overall {sector} figure")
    return name, notes, _not_comparable(by_period, lines, below, sector), caveat


def _plan_line_detail(ind, rows: list[dict], periods: list, values: list) -> dict:
    """What _plan_line says, as data: "notes" (one per period with plan lines: {"kind":
    "plan_line", "year", "lines", "figure", "below", "sector_en", "sector_tr"}), "years"
    (which of the series' years are "below" a sub-line, possibly a "line", or the plan's
    "single" figure) and "caveat" for the latest figure ("not_overall", "maybe_not_overall"
    or None)."""
    lines = sub_sector_lines(rows, ind)
    by_period = {str(p)[:10]: v for p, v in zip(periods, values)}
    lines = {p: subs for p, subs in lines.items() if p in by_period}
    if not lines:
        return {"notes": [], "years": None, "caveat": None}

    def below(period):
        return any(v > by_period[period] for _, v in lines.get(period, []))

    notes = [{"kind": "plan_line", "year": period[:4], "lines": subs,
              "figure": by_period[period], "below": below(period),
              "sector_en": ind.sector_en or "the sector", "sector_tr": ind.sector_tr or "sektör"}
             for period, subs in lines.items()]
    years: dict[str, list[str]] = {}
    for period in sorted(by_period):
        kind = "single" if period not in lines else ("below" if below(period) else "line")
        years.setdefault(kind, []).append(period[:4])
    latest = str(periods[-1])[:10]
    caveat = None
    if latest in lines:
        caveat = "not_overall" if below(latest) else "maybe_not_overall"
    return {"notes": notes, "years": years, "caveat": caveat}


def _not_comparable(by_period: dict, lines: dict, below, sector: str) -> str | None:
    """Why a series' years are not comparable, or None. Only years whose plan reports
    the sector as one figure compare with each other: any year that is one of several
    plan lines may be a different line from the next."""
    if len(by_period) < 2 or not lines:
        return None
    kinds = {
        "below": f"one of the plan's separate {sector} lines, not its overall figure",
        "line": f"possibly one of the plan's separate {sector} lines rather than its overall figure",
        "single": f"the plan's only {sector} figure",
    }
    years: dict[str, list[str]] = {}
    for period in sorted(by_period):
        kind = "single" if period not in lines else ("below" if below(period) else "line")
        years.setdefault(kind, []).append(period[:4])
    parts = [f"{', '.join(ys)}: {kinds[k]}" for k, ys in years.items()]
    return "; ".join(parts) + "; HDX HAPI does not say which line each year's figure is"


# Where a reader can open HDX HAPI when HAPI cannot name the dataset behind a series.
_HAPI_PAGE = "https://hapi.humdata.org/"


def data_sources(findings: Findings, country: str, retrieved: str | None = None) -> list[dict]:
    """The report's source list: one entry per series it used, in the shape of a
    report's document sources (index, title, url, source, date, country) with
    doctype "dataset" and the period covered and the day retrieved. The url is the HDX
    dataset page (never a HAPI request, which would carry the app identifier)."""
    retrieved = retrieved or _today().isoformat()
    out = []
    looked_up: dict[str, dict | None] = {}    # one lookup per resource, failed or not
    for i, used in enumerate(findings.data_sources, start=1):
        rid = used.get("resource_hdx_id")
        if rid and rid not in looked_up:
            looked_up[rid] = resource_metadata(rid)
        meta = looked_up.get(rid) if rid else None
        first, last = used["first_period"], used["last_period"]
        entry = {"index": i, "title": used["title"],
                 "url": (f"https://data.humdata.org/dataset/{meta['dataset_hdx_stub']}"
                         if meta else _HAPI_PAGE),
                 "source": used["source"], "date": last, "country": country,
                 "doctype": "dataset"}
        if meta and meta.get("dataset_hdx_title"):
            entry["dataset"] = meta["dataset_hdx_title"]
        # No word in it: the same text reads right under a Turkish or an English report.
        entry["period"] = first if first == last else f"{first} – {last}"
        entry["retrieved"] = retrieved
        out.append(entry)
    return out


def _series(rows: list[dict], ind, date_from: str, date_to: str, today: date):
    """The indicator's rows and national series for one window, with the notes on
    what was left out of it: (rows, notes, periods, values)."""
    rows, notes, _, periods, values = _series_detail(rows, ind, date_from, date_to, today)
    return rows, notes, periods, values


def _series_detail(rows: list[dict], ind, date_from: str, date_to: str, today: date):
    """_series with the notes also as data: (rows, notes, items, periods, values). Each
    item is {"kind": "dtm" | "ipc" | "totals", …}, in the notes' order."""
    rows = _filter_period(rows, date_from, date_to)
    if ind.complete_periods_only:
        rows = _completed(rows, today)
    _, left_out = snapshot_selection(rows)
    rows, note = consistent_snapshots(rows)
    coverage, span = ipc_coverage_note(rows), ipc_coverage(rows)
    periods, values = national_series(rows, ind)
    totals, years = competing_totals_note(rows, ind, fmt=_full), competing_totals(rows, ind)
    items = (([{"kind": "dtm", **left_out}] if left_out else [])
             + ([{"kind": "ipc", "low": span[0], "high": span[1]}] if span else [])
             + ([{"kind": "totals", "years": years}] if years else []))
    return rows, [n for n in (note, coverage, totals) if n], items, periods, values


def _value_unit(ind) -> str:
    """How a value of the indicator is written in the findings: '%', 'USD' or 'people'."""
    if ind.scale == 100:
        return "%"
    return "USD" if ind.key == "funding" else "people"


def _value(value: float, unit: str) -> str:
    return f"{_plain(value)}%" if unit == "%" else f"{_plain(value)} {unit}"


def _observations(n: int) -> str:
    return "no observation" if n == 0 else f"{n} observation{'' if n == 1 else 's'}"


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
    family = sum(1 for p in adjusted if p is not None)
    for s, p_adj in zip(sections, adjusted):
        s.stat_result["family"] = family
        # Untested (no p-value): outside the Holm family, and no verdict to narrate.
        s.stat_result["tested"] = s.stat_result.get("p_value") is not None
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
    """The test's p-value and the code's verdict; the Holm-adjusted p only when the report
    ran two or more tests (with one there is no correction to report)."""
    verdict = f"{'SIGNIFICANT' if r['significant'] else 'NOT SIGNIFICANT'} (α=0.05)"
    if r.get("family", 2) < 2:
        return f"{_fmt_p(r['p_value'])} → {verdict}"
    return f"{_fmt_p(r['p_value'])}, Holm-adjusted {_fmt_p(r['p_adjusted'])} → {verdict}"


_NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                 "ten", "eleven", "twelve"]


def _count(n: int) -> str:
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else str(n)


def _plain(x: float) -> str:
    """A value as the model should repeat it: three significant digits for large
    magnitudes (931170.92 → 931000), one decimal from 10, two below. The report
    used to quote slopes and intervals to the cent ("-931,170.92 people a year")."""
    if x == 0 or not math.isfinite(x):
        return f"{x:g}"
    if abs(x) >= 1000:
        return f"{round(x, 2 - int(math.floor(math.log10(abs(x))))):.0f}"
    return f"{x:.1f}" if abs(x) >= 10 else f"{x:.2f}"


_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]


def _day(iso: str) -> str:
    """'2026-11-18' -> '18 November 2026' (a chosen period's ends: the day matters)."""
    d = date.fromisoformat(str(iso)[:10])
    return f"{d.day} {_MONTHS_EN[d.month - 1]} {d.year}"


def _when(period, resolution: str = "month") -> str:
    """A reference period at the data's resolution: '2026' (yearly) or 'March 2022'."""
    d = date.fromisoformat(str(period)[:10])
    return str(d.year) if resolution == "year" else f"{_MONTHS_EN[d.month - 1]} {d.year}"


def _amount(value: float, unit: str) -> str:
    """A value as a reader reads it and the model repeats it: '17.4 million people',
    '443,000 people', '6,510 people', '1.16 billion USD', '32.0%'."""
    if unit == "%":
        return f"{_plain(value)}%"
    if value and abs(value) < 0.5:
        return f"about 0 {unit}"            # never "-0 people per year"
    sign, a = ("-" if value < 0 else ""), abs(value)
    if a >= 1000:
        a = round(a, 2 - int(math.floor(math.log10(a))))   # three significant digits first:
    for scale, word in ((1e9, "billion"), (1e6, "million")):   # 999,600 -> 1.00 million
        if a >= scale:
            m = a / scale
            decimals = max(0, 2 - int(math.floor(math.log10(m))))
            text = f"{m:.{decimals}f} {word}"
            break
    else:
        text = f"{int(round(a)):,}"
    return f"{sign}{text} {unit}"


def _amounts(values: list[float], unit: str, exact: bool = False) -> list[str]:
    """The values in reader form, or in full when the reader form would print two
    different values alike (or the series has plan lines to tell apart)."""
    if unit != "%" and (exact or len({_amount(v, unit) for v in values}) < len(set(values))):
        return [f"{_full(v)} {unit}" for v in values]
    return [_amount(v, unit) for v in values]


def _rate(value: float, r: dict) -> str:
    """A slope or interval bound per year, in the indicator's unit."""
    if r.get("unit") == "percentage points":
        return f"{_plain(value)} percentage points"
    return _amount(value, r.get("value_unit") or "people")


def _trend_text(r: dict) -> str:
    """Latest value first, against the first one of the window; then the test."""
    res = r.get("resolution", "month")
    first, last = _when(r["first_period"], res), _when(r["last_period"], res)
    lb = r.get("look_back")
    before = ", before the chosen period" if lb and not lb["chosen_points"] else ""
    window = "Trend over the look-back window" if lb else "Trend"
    if r.get("line_change") is not None:
        change = f"; change along the trend line {r['line_change']:+.1f} percentage points"
    elif r["pct_change"] is not None:
        change = f"; relative change along the trend line {r['pct_change']:+.1f}%"
    else:
        change = ""         # no relative change from a start at or below zero
    if r["ci_low"] is None:
        ci = "95% CI: too few points"
    elif r.get("unit") == "percentage points":
        ci = f"95% CI {_plain(r['ci_low'])} to {_plain(r['ci_high'])} percentage points"
    else:
        ci = f"95% CI {_rate(r['ci_low'], r)} to {_rate(r['ci_high'], r)}"
    return (f"{r['indicator']}: latest value {_amount(r['latest_value'], r['value_unit'])} "
            f"({last}{before}), against {_amount(r['first_value'], r['value_unit'])} in {first}. "
            f"{window}, {first} to {last}: {r['direction']}, Sen slope {_rate(r['slope'], r)} per "
            f"year ({ci}), Kendall tau {r['tau']:.2f}, Mann-Kendall {_verdict(r)}{change}; "
            f"{_count(r['n_points'])} observations.")


def _region_text(r: dict) -> str:
    unit = r.get("value_unit", "people")
    top = ", ".join(f"{name} ({_amount(val, unit)})" for name, val in r["ranking"][:3])
    res = r.get("resolution", "month")
    first, last = _when(r["first_period"], res), _when(r["last_period"], res)
    when = f"as of {first}" if first == last else f"(mean per region, {first} to {last})"
    if r["p_value"] is None:
        # Not tested: a ranking for the stated date, never a "not significant" result.
        why = ("one observation per region" if r["max_obs"] <= 1
               else "fewer than two regions have two or more observations")
        return (f"{r['indicator']}: highest regions {when}: {top}; a statistical comparison "
                f"between regions was not possible: {why}.")
    h = "n/a" if r["kruskal_h"] is None else f"{r['kruskal_h']:.2f}"
    return (f"{r['indicator']}: highest regions {when}: {top}; difference between regions "
            f"Kruskal-Wallis H={h}, {_verdict(r)}.")


def _correlation_text(r: dict) -> str:
    coef = "n/a" if r["coefficient"] is None else f"{r['coefficient']:.2f}"
    return (f"{r['indicator_x']} ↔ {r['indicator_y']}: {r['method']} r={coef}, "
            f"{_verdict(r)}; {_count(r['n_points'])} common periods.")


def _snapshot_text(r: dict) -> str:
    """A series too short for a trend: its latest value first, the earlier ones after
    it (compared only when the years are comparable), and in a few words why no test."""
    res, unit = r.get("resolution", "month"), r["value_unit"]
    points = list(zip(r["periods"], r["values"]))
    n = len(points)
    lb = r.get("look_back")
    name = f"{r['indicator']} (look-back window)" if lb else r["indicator"]
    before = ", before the chosen period" if lb and not lb["chosen_points"] else ""
    shown = _amounts([v for _, v in points], unit, r.get("exact", False))
    (lp, lv), latest = points[-1], shown[-1]
    text = f"{name}: latest value {latest} ({_when(lp, res)}{before})"
    if n > 1:
        if not r.get("not_comparable"):
            (pp, pv), previous = points[-2], shown[-2]
            move = "up from" if lv > pv else ("down from" if lv < pv else "the same as")
            text += f", {move} {previous} in {_when(pp, res)}"
            earlier = list(zip(points, shown))[:-2]
        else:
            earlier = list(zip(points, shown))[:-1]
        if earlier:
            text += "; earlier " + ", ".join(
                f"{a} in {_when(p, res)}" for (p, _), a in reversed(earlier))
    text += "."
    if r.get("not_comparable"):
        text += (f" The values are not comparable across years ({r['not_comparable']}), "
                 f"so no trend is tested.")
    elif n >= r["min_points"]:
        text += " The values do not vary, so no trend is tested."
    else:
        text += f" {_count(n).capitalize()} observation{'' if n == 1 else 's'}: too few for a trend test."
    return text


_TEXT = {"trend": _trend_text, "region": _region_text, "correlation": _correlation_text,
         "snapshot": _snapshot_text}


def findings_to_context(findings: Findings) -> str:
    # Her bölümün başlığı '## ' satırı olarak VERBATIM (kod-üretimli, s.heading) taşınır.
    # Render tarafı (report_pdf.py / reportImages.js) grafiği bu başlığa göre LLM çıktısındaki
    # '## ' başlığıyla eşleştirir — LLM başlığı burada göremezse kendi başlığını uydurur ve
    # grafik hiçbir zaman eşleşmez (bkz. FIX I1). Bu yüzden başlık LLM'e aynen verilir; prompt
    # bunu değiştirmeden kopyalamasını zorunlu kılar.
    lines = ["COMPUTED STATISTICAL FINDINGS (do not recompute — narrate only):", ""]
    if findings.date_from:
        chosen = (f" (no period was chosen: the last {_count(findings.default_years)} years)"
                  if findings.default_years else "")
        lines += [f"PERIOD ANALYSED: {_day(findings.date_from)} to {_day(findings.date_to)}"
                  f"{chosen}", ""]
    if findings.headline:
        lines += ["HEADLINE (the sector's own figures; open the Executive Summary with them): "
                  + " ".join(findings.headline), ""]
    # The look-back, once for the report: the sections only mark "(look-back window)".
    looked = [s.stat_result for s in findings.sections if s.stat_result.get("look_back")]
    if looked:
        names = ", ".join(dict.fromkeys(r["indicator"] for r in looked))
        lb = looked[0]["look_back"]
        lines += [f"LOOK-BACK: the chosen period holds too few observations for {names}, so their "
                  f"values and trends below cover the longer look-back window {_day(lb['date_from'])} "
                  f"to {_day(lb['date_to'])} (marked “look-back window”).", ""]
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
    tested_kinds = [s.stat_result["kind"] for s in findings.sections
                    if s.stat_result.get("p_value") is not None]
    tested = len(tested_kinds)
    if not tested:
        # Nothing was tested: no test methods to restate, no Holm family.
        lines += [
            "METHOD NOTES:",
            "- No statistical test was possible: every finding is reported as its observed values.",
            "- Limitation: the series are short, so the values are descriptive.",
        ]
        return "\n".join(lines)
    # Only the methods this report used (a report with one trend test used to list the
    # regional and correlation tests and "Holm correction across all 1 tests").
    lines.append("METHOD NOTES:")
    if "trend" in tested_kinds:
        lines.append("- Trend: Mann-Kendall test; the slope is Sen's slope per year on the real "
                     "dates of the periods; Kendall tau is the effect size.")
    if "region" in tested_kinds:
        lines.append("- Regions: Kruskal-Wallis test across admin-1 regions.")
    if "correlation" in tested_kinds:
        lines.append(f"- Correlation: Pearson, for indicator pairs with at least "
                     f"{CORRELATION_MIN_POINTS} common periods.")
    if tested >= 2:
        lines.append(f"- Multiple comparisons: Holm correction across all {_count(tested)} tests "
                     f"in this report; significance is decided on the Holm-adjusted p-value at "
                     f"α=0.05.")
    else:
        lines.append("- One statistical test was run, so no multiple-comparison correction "
                     "applies; significance is decided on its p-value at α=0.05.")
    lines.append("- Limitation: the series are short; the tests assume independent observations "
                 "and serial correlation between consecutive periods is not corrected for, so the "
                 "results are indicative.")
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
