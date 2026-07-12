"""HAPI satırlarını istatistik motorunun beklediği seri yapılarına dönüştürür.

national_series: dönem×ulusal-toplam zaman serisi (indicator.filters uygulanır,
aggregation ile birleştirilir). regional_series: admin1 bölgesi başına dönemsel
seri (bölgeler-arası test için). pandas ile gruplama; sayısal olmayan değerler
sessizce düşürülür.
"""
import logging

import pandas as pd

from analytics.indicators import Indicator

logger = logging.getLogger(__name__)


def _frame(rows: list[dict], indicator: Indicator) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for key, val in indicator.filters.items():
        if key in df.columns:
            df = df[df[key] == val]
    if indicator.value_field not in df.columns or "reference_period_start" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["_value"] = pd.to_numeric(df[indicator.value_field], errors="coerce")
    df = df.dropna(subset=["_value", "reference_period_start"])
    return df


def has_required_filter_columns(rows: list[dict], indicator: Indicator) -> bool:
    """indicator.filters uygulanabilir mi? Filtre yoksa her zaman True. Satırlar
    boşsa karar national_series'in kendi 'veri yok' dalına bırakılır (True).
    Filtre alanı satırlarda hiç yoksa False — çağıran, double-counting riskine
    karşı bu indikatörü unfiltered toplamak yerine gap'e düşürmeli."""
    if not indicator.filters or not rows:
        return True
    columns: set[str] = set()
    for r in rows:
        columns.update(r.keys())
    return all(key in columns for key in indicator.filters)


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
    )
    grouped = grouped.sort_index()
    periods = [str(p) for p in grouped.index.tolist()]
    values = [float(v) for v in grouped.tolist()]
    return periods, values


def regional_series(rows: list[dict], indicator: Indicator) -> dict[str, list[float]]:
    df = _frame(rows, indicator)
    if df.empty or "admin1_name" not in df.columns:
        return {}
    out: dict[str, list[float]] = {}
    for region, sub in df.groupby("admin1_name"):
        per_period = sub.groupby("reference_period_start")["_value"].apply(
            lambda s: _agg(s, indicator.aggregation)
        ).sort_index()
        out[str(region)] = [float(v) for v in per_period.tolist()]
    return out
