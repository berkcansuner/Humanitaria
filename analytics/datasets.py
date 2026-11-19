"""HAPI satırlarını istatistik motorunun beklediği seri yapılarına dönüştürür.

Sunucu-tarafı query_params agregat satırları getirdiğinden client-tarafı filtre
gerekmez; tek istisna humanitarian-needs endpoint'inin (her sektör, INN) `category`
kırılımıdır — dönem-agregat satırı (boş/None/'total' kategorisi) dedup edilir,
aksi hâlde demografik alt-kırılımlar toplanıp şişik değer üretir.
"""
import logging

import pandas as pd

from analytics.indicators import Indicator

logger = logging.getLogger(__name__)


# Below this share of the 'total' row, an undisaggregated ('') row is a stray sub-line,
# not the sector total (Nigeria CCCM 2024: 780 vs 2,487,269; Myanmar 2025: 1,957,173 vs
# 19,902,649 people in need).
_STRAY_SHARE = 0.5
# Under a parent code that also carries sub-lines (PRO beside PRO-CPN …), the plan's other
# lines leak into the undisaggregated row: Haiti 2025's '' row under PRO is the migrants
# line (349,999) while 'total' is the general line's breakdown total (466,589); Nigeria
# 2024's '' row (5,093,865, 2% below its 'total') is the published overall figure.
_STRAY_SHARE_BESIDE_SUB_LINES = 0.9


def _published_total(totals: dict, beside_sub_lines: bool = False) -> tuple[str, float]:
    """('', value) or ('total', value): the figure the HNO publishes for one period.
    Checked against the plans' published caseloads (HPC Tools, 2026-11-18): the
    undisaggregated row is the published figure unless it is far below the 'total' row."""
    blank, total = totals.get(""), totals.get("total")
    share = _STRAY_SHARE_BESIDE_SUB_LINES if beside_sub_lines else _STRAY_SHARE
    if blank is None or (total is not None and blank < share * total):
        return "total", total
    return "", blank


def _sub_line_periods(df: pd.DataFrame, indicator: Indicator) -> set:
    """Periods in which HAPI returned sub-sector rows beside the indicator's sector."""
    code = indicator.query_params.get("sector_code")
    if not code or "sector_code" not in df.columns:
        return set()
    sub = df[df["sector_code"].astype(str).str.startswith(f"{code}-")]
    return set(sub["reference_period_start"].astype(str))


def _dedup_aggregate_rows(df: pd.DataFrame, indicator: Indicator,
                          sub_periods: set | None = None) -> pd.DataFrame:
    if indicator.endpoint == "affected-people/humanitarian-needs" and "category" in df.columns:
        cat = df["category"].fillna("").astype(str).str.strip().str.lower()
        df = df[cat.isin(["", "total"])].assign(_cat=cat)
        # One row per period: the published total of its '' and 'total' rows (each the
        # largest of its kind, against sub-set rows leaking from an unpinned dimension).
        keep = []
        for period, sub in df.groupby("reference_period_start"):
            best = sub.sort_values("_value", ascending=False).drop_duplicates("_cat")
            chosen, _ = _published_total(dict(zip(best["_cat"], best["_value"])),
                                         str(period) in (sub_periods or set()))
            keep.append(best[best["_cat"] == chosen].index[0])
        df = df.loc[keep].drop(columns="_cat")
    return df


def _exact(df: pd.DataFrame, indicator: Indicator) -> pd.DataFrame:
    """Rows whose server-side filter columns equal the requested values exactly. HAPI
    matches some filters by prefix: sector_code=PRO also returns PRO-CPN, PRO-GBV,
    PRO-HLP and PRO-MIN, whose larger figures then passed for the protection total."""
    for col, wanted in indicator.query_params.items():
        if col in df.columns:
            df = df[df[col].astype(str) == str(wanted)]
    return df


def _frame(rows: list[dict], indicator: Indicator, dedup: bool = True) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if indicator.value_field not in df.columns or "reference_period_start" not in df.columns:
        return pd.DataFrame()
    sub_periods = _sub_line_periods(df, indicator)
    df = _exact(df, indicator).copy()
    df["_value"] = pd.to_numeric(df[indicator.value_field], errors="coerce") * indicator.scale
    df = df.dropna(subset=["_value", "reference_period_start"])
    if not dedup:
        return df.assign(_beside_sub_lines=df["reference_period_start"].astype(str).isin(sub_periods))
    return _dedup_aggregate_rows(df, indicator, sub_periods)


def _agg(series: pd.Series, how: str) -> float:
    if how == "mean":
        return float(series.mean())
    if how == "latest":
        return float(series.iloc[-1])
    return float(series.sum())


def national_series(rows: list[dict], indicator: Indicator) -> tuple[list[str], list[float]]:
    df = _frame(rows, indicator)
    if df.empty:
        return [], []
    grouped = df.groupby("reference_period_start")["_value"].apply(
        lambda s: _agg(s, indicator.aggregation)
    ).sort_index()
    periods = [str(p) for p in grouped.index.tolist()]
    values = [float(v) for v in grouped.tolist()]
    return periods, values


def regional_series(rows: list[dict], indicator: Indicator) -> dict[str, list[float]]:
    df = _frame(rows, indicator)
    if df.empty or "admin1_name" not in df.columns:
        return {}
    df = df[df["admin1_name"].notna()]
    if df.empty:
        return {}
    out: dict[str, list[float]] = {}
    for region, sub in df.groupby("admin1_name"):
        per_period = sub.groupby("reference_period_start")["_value"].apply(
            lambda s: _agg(s, indicator.aggregation)
        ).sort_index()
        out[str(region)] = [float(v) for v in per_period.tolist()]
    return out


_TOTALS_DIFFER = 0.01   # '' and 'total' rows further apart than this share are noted


def two_totals_periods(rows: list[dict], indicator: Indicator) -> dict[str, dict]:
    """period (YYYY-MM-DD) -> {'': value, 'total': value} for the periods whose two
    totals differ by more than _TOTALS_DIFFER."""
    df = _frame(rows, indicator, dedup=False)
    if df.empty or "category" not in df.columns:
        return {}
    cat = df["category"].fillna("").astype(str).str.strip().str.lower()
    out = {}
    for period, sub in df.assign(_cat=cat)[cat.isin(["", "total"])].groupby("reference_period_start"):
        totals = sub.groupby("_cat")["_value"].max().to_dict()
        if len(totals) == 2 and abs(totals[""] - totals["total"]) > _TOTALS_DIFFER * max(totals.values()):
            out[str(period)[:10]] = {**totals, "beside_sub_lines": bool(sub["_beside_sub_lines"].any())}
    return out


def competing_totals(rows: list[dict], indicator: Indicator) -> list[dict]:
    """One entry per year whose two totals differ: {"year", "blank", "total", "used"}
    ("used": '' or 'total', the row _published_total picks)."""
    out = []
    for period, totals in two_totals_periods(rows, indicator).items():
        chosen, _ = _published_total(totals, totals["beside_sub_lines"])
        out.append({"year": period[:4], "blank": totals[""], "total": totals["total"],
                    "used": chosen})
    return out


def competing_totals_note(rows: list[dict], indicator: Indicator,
                          fmt=lambda v: str(int(v))) -> str | None:
    """HNO rows carry a sector's total twice per year: the undisaggregated row
    (category '') and the 'total' of its breakdown. They usually agree. When they do
    not, _published_total picks one, and the note says which, because HDX HAPI does not
    hold every published sector total: where a plan splits a cluster into sub-lines
    (Haiti protection 2025: migrants 349,999, general protection 466,589, protection
    total 2,160,007) HAPI keeps two sub-lines and neither is the sector figure."""
    years = []
    for t in competing_totals(rows, indicator):
        blank = f"{fmt(t['blank'])} without a breakdown" + (" (used)" if t["used"] == "" else "")
        total = f"{fmt(t['total'])} as the total of its breakdown" + (
            " (used)" if t["used"] == "total" else "")
        years.append(f"{t['year']}: {blank} and {total}")
    if not years:
        return None
    return (f"HDX HAPI holds two totals for {'; '.join(years)}; the HNO's published sector "
            f"figure may differ")


def sub_sector_lines(rows: list[dict], indicator: Indicator) -> dict[str, list[tuple[str, float]]]:
    """period -> [(sub-line name, figure)] for the sub-sectors HAPI returns beside a
    sector (sector_code=PRO also brings PRO-CPN, PRO-GBV, PRO-HLP, PRO-MIN). Each
    sub-line's figure is its published total; the lines are never added up, since a
    person can be counted in more than one. Empty for an indicator without sector_code."""
    code = indicator.query_params.get("sector_code")
    if not code or not rows:
        return {}
    df = pd.DataFrame(rows)
    if "sector_code" not in df.columns or "reference_period_start" not in df.columns:
        return {}
    df = df[df["sector_code"].astype(str).str.startswith(f"{code}-")].copy()
    if df.empty:
        return {}
    df["_value"] = pd.to_numeric(df[indicator.value_field], errors="coerce")
    df = df.dropna(subset=["_value"])
    cat = df.get("category", pd.Series("", index=df.index)).fillna("").astype(str).str.strip().str.lower()
    df = df[cat.isin(["", "total"])].assign(_cat=cat)
    out: dict[str, list[tuple[str, float]]] = {}
    for (period, sub_code), sub in df.groupby(["reference_period_start", "sector_code"]):
        totals = sub.groupby("_cat")["_value"].max().to_dict()
        _, value = _published_total(totals)
        name = str(sub["sector_name"].iloc[0]) if "sector_name" in sub.columns else str(sub_code)
        out.setdefault(str(period)[:10], []).append((name, float(value)))
    return {p: sorted(lines) for p, lines in sorted(out.items())}


_COMPLETE_SHARE = 0.8  # a snapshot must cover at least this share of the operation's regions


def snapshot_selection(rows: list[dict]) -> tuple[list[dict], dict | None]:
    """One DTM operation, complete rounds only (IDPs), and what was left out:
    {"operation", "other_operations", "incomplete_rounds"} (None when nothing was).

    HAPI returns several displacement-tracking operations for a country, each
    counting differently (a countrywide overview, an event's new displacement, an
    old caseload in a few regions), and a round may cover only part of the regions.
    Summing all of it per date mixed definitions and coverage. Kept: the operation
    covering the most regions in one snapshot, then the most recent, then the one
    with the most snapshots; within it, snapshots covering at least 80% of its
    regions. Rows without an operation are returned unchanged."""
    if not any(r.get("operation") for r in rows):
        return rows, None
    snapshots: dict[str, dict[str, set]] = {}          # operation -> date -> regions
    for r in rows:
        op = r.get("operation") or ""
        date = str(r.get("reference_period_start"))[:10]
        snapshots.setdefault(op, {}).setdefault(date, set()).add(r.get("admin1_name"))

    def rank(op):
        dates = snapshots[op]
        return (max(len(regions) for regions in dates.values()), max(dates), len(dates))

    chosen = max(snapshots, key=rank)
    widest = rank(chosen)[0]
    complete = {d for d, regions in snapshots[chosen].items() if len(regions) >= _COMPLETE_SHARE * widest}
    kept = [r for r in rows if (r.get("operation") or "") == chosen
            and str(r.get("reference_period_start"))[:10] in complete]
    dropped_ops = len(snapshots) - 1
    dropped_rounds = len(snapshots[chosen]) - len(complete)
    if not dropped_ops and not dropped_rounds:
        return rows, None
    return kept, {"operation": chosen, "other_operations": dropped_ops,
                  "incomplete_rounds": dropped_rounds}


def consistent_snapshots(rows: list[dict]) -> tuple[list[dict], str | None]:
    """snapshot_selection with its note in English (None when nothing was left out)."""
    kept, left_out = snapshot_selection(rows)
    if left_out is None:
        return kept, None
    parts = [f"only the DTM operation '{left_out['operation']}' is used"]
    if left_out["other_operations"]:
        parts.append(f"{left_out['other_operations']} other operation(s) count displacement "
                     f"differently and are not mixed in")
    if left_out["incomplete_rounds"]:
        parts.append(f"{left_out['incomplete_rounds']} incomplete round(s) covering under 80% "
                     f"of its regions are left out")
    return kept, "; ".join(parts)


_COVERAGE_CHANGE = 1.2   # analysed population varying more than this factor is noted


def ipc_coverage(rows: list[dict]) -> tuple[float, float] | None:
    """(smallest, largest) analysed population when IPC analyses covered very different
    populations across periods (people in phase / share in phase = population analysed);
    None when coverage is stable or the rows are not IPC rows."""
    analysed = [r["population_in_phase"] / r["population_fraction_in_phase"] for r in rows
                if r.get("population_in_phase") and r.get("population_fraction_in_phase")]
    if not analysed or max(analysed) <= _COVERAGE_CHANGE * min(analysed):
        return None
    return min(analysed), max(analysed)


def ipc_coverage_note(rows: list[dict]) -> str | None:
    """Why the IPC series uses the share, in English (None when coverage is stable)."""
    span = ipc_coverage(rows)
    if span is None:
        return None
    return (f"IPC analyses covered different parts of the country in different periods "
            f"(analysed population {span[0] / 1e6:.1f} to {span[1] / 1e6:.1f} million), "
            f"so the share of the analysed population is used, not the number of people")
