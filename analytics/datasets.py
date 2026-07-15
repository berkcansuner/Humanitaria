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
    df["_value"] = pd.to_numeric(df[indicator.value_field], errors="coerce")
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
