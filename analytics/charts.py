"""Teknik izleme raporu için matplotlib grafikleri → base64 PNG data-URI.

Başsız Agg backend (import sırasında ayarlanır). Her fonksiyon rapora gömülebilir
'data:image/png;base64,...' döndürür (mevcut section_images formatı ile uyumlu).
Temiz stil: başlık, eksen etiketleri, ızgara.
"""
import base64
import io
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)

_FIGSIZE = (8, 4.5)
_DPI = 120


def _to_datauri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def trend_chart(periods, values, slope, intercept, title: str, ylabel: str) -> str:
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    x = list(range(len(values)))
    ax.plot(x, values, marker="o", color="#1f77b4", label="Gözlem")
    if slope is not None and intercept is not None:
        line = [intercept + slope * i for i in x]
        ax.plot(x, line, color="#d62728", linestyle="--", label="Trend (OLS)")
        ax.legend()
    ax.set_xticks(x)
    ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=8)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    return _to_datauri(fig)


def comparison_chart(labels, values, title: str, ylabel: str) -> str:
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar(labels, values, color="#2ca02c")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, axis="y", alpha=0.3)
    return _to_datauri(fig)


def correlation_chart(x, y, xlabel: str, ylabel: str, title: str) -> str:
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.scatter(x, y, color="#9467bd")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    return _to_datauri(fig)
