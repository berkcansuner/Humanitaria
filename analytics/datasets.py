"""HAPI satırlarını istatistik motorunun beklediği seri yapılarına dönüştürür.

Sunucu-tarafı query_params agregat satırları getirdiğinden client-tarafı filtre
gerekmez; tek istisna humanitarian_needs'in Intersectoral+INN içindeki `category`
kırılımıdır — dönem-agregat satırı (boş/None/'total' kategorisi) dedup edilir,
aksi hâlde demografik alt-kırılımlar toplanıp şişik değer üretir.
"""
import logging

import pandas as pd

from analytics.indicators import Indicator

logger = logging.getLogger(__name__)


def _dedup_aggregate_rows(df: pd.DataFrame, indicator: Indicator) -> pd.DataFrame:
    if indicator.key == "humanitarian_needs" and "category" in df.columns:
        cat = df["category"].fillna("").astype(str).str.strip().str.lower()
        df = df[cat.isin(["", "total"])]
        # Dönem başına en büyük (= sektörler-arası toplam) satırı tut: sabitlenmemiş
        # bir boyuttan sızan alt-küme satırlarına ve '' / 'total' çift kaydına karşı sağlam.
        df = df.sort_values("_value", ascending=False).drop_duplicates(
            subset=["reference_period_start"], keep="first")
    return df


def _frame(rows: list[dict], indicator: Indicator) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if indicator.value_field not in df.columns or "reference_period_start" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["_value"] = pd.to_numeric(df[indicator.value_field], errors="coerce") * indicator.scale
    df = df.dropna(subset=["_value", "reference_period_start"])
    df = _dedup_aggregate_rows(df, indicator)
    return df


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


_COMPLETE_SHARE = 0.8   # a snapshot must cover at least this share of the operation's regions


def consistent_snapshots(rows: list[dict]) -> tuple[list[dict], str | None]:
    """One DTM operation, complete rounds only (IDPs).

    HAPI returns several displacement-tracking operations for a country, each
    counting differently (a countrywide overview, an event's new displacement, an
    old caseload in a few regions), and a round may cover only part of the regions.
    Summing all of it per date mixed definitions and coverage. Kept: the operation
    covering the most regions in one snapshot, then the most recent, then the one
    with the most snapshots; within it, snapshots covering at least 80% of its
    regions. Rows without an operation are returned unchanged. The note (None when
    nothing was left out) tells the report what was used."""
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
    parts = [f"only the DTM operation '{chosen}' is used"]
    if dropped_ops:
        parts.append(f"{dropped_ops} other operation(s) count displacement differently and are not mixed in")
    if dropped_rounds:
        parts.append(f"{dropped_rounds} incomplete round(s) covering under 80% of its regions are left out")
    return kept, "; ".join(parts)


_COVERAGE_CHANGE = 1.2   # analysed population varying more than this factor is noted


def ipc_coverage_note(rows: list[dict]) -> str | None:
    """A note when IPC analyses covered very different populations across periods
    (people in phase / share in phase = population analysed) — why the series uses
    the share. None when coverage is stable or the rows are not IPC rows."""
    analysed = [r["population_in_phase"] / r["population_fraction_in_phase"] for r in rows
                if r.get("population_in_phase") and r.get("population_fraction_in_phase")]
    if not analysed or max(analysed) <= _COVERAGE_CHANGE * min(analysed):
        return None
    return (f"IPC analyses covered different parts of the country in different periods "
            f"(analysed population {min(analysed) / 1e6:.1f} to {max(analysed) / 1e6:.1f} million), "
            f"so the share of the analysed population is used, not the number of people")
