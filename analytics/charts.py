"""Teknik izleme raporu için matplotlib grafikleri → base64 PNG data-URI.

Başsız Agg backend (import sırasında ayarlanır). Her fonksiyon rapora gömülebilir
'data:image/png;base64,...' döndürür (mevcut section_images formatı ile uyumlu).
Temiz stil: başlık, eksen etiketleri, ızgara.
"""
import base64
import io
import logging
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

logger = logging.getLogger(__name__)

_FIGSIZE = (8, 4.5)
_DPI = 120

# The app's "Quiet Archive" colours, light and dark (frontend/src/style.css): page
# background, text, secondary text and border tokens. `series` is the accent green;
# `reference` (the Sen trend line) is an orange chosen to stay distinct from it under
# colour-vision deficiency. Both pairs pass the dataviz palette validator (lightness
# band, chroma, CVD and normal-vision separation, 3:1 contrast) on their own surface.
_THEMES = {
    "light": {"bg": "#faf9f6", "text": "#1a1c1a", "muted": "#5f5e5e", "grid": "#e3e2e0",
              "series": "#036a34", "reference": "#eb6834"},
    "dark": {"bg": "#0f1412", "text": "#e6edea", "muted": "#a9b2ad", "grid": "#28302c",
             "series": "#2fae6c", "reference": "#c4501a"},
}

# Legend text in the report language (the report itself is "tr" or "en").
_LEGEND = {
    "tr": {"observed": "Gözlem", "trend": "Trend (Sen)"},
    "en": {"observed": "Observed", "trend": "Trend (Sen)"},
}


_MONTHS = {
    "tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
# Compact suffixes from 10,000 up; below that numbers are written in full.
_SUFFIXES = {
    "tr": [(1e9, " mr"), (1e6, " mn"), (1e3, " bin")],
    "en": [(1e9, "B"), (1e6, "M"), (1e3, "K")],
}


def _number(value: float, language: str, decimals: int = 2) -> str:
    """Up to *decimals* places, trailing zeros dropped, in the language's separators
    (en 1,234.5 · tr 1.234,5)."""
    text = f"{value:,.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if language == "tr":
        text = text.translate(str.maketrans({",": ".", ".": ","}))
    return text


def format_value(value: float, language: str = "tr", percent: bool = False) -> str:
    """Axis/label text for a value: '45%' / '%45' for shares, otherwise full under
    10,000 and compact above it ('2.5M' / '2,5 mn')."""
    if percent:
        num = _number(value, language, 1)
        return f"%{num}" if language == "tr" else f"{num}%"
    for limit, suffix in _SUFFIXES.get(language, _SUFFIXES["en"]):
        if abs(value) >= max(limit, 1e4):
            return _number(value / limit, language) + suffix
    return _number(value, language, 0)


def _value_axis(axis, language: str, percent: bool = False) -> None:
    axis.set_major_locator(MaxNLocator(nbins=5))
    axis.set_major_formatter(FuncFormatter(lambda v, _pos: format_value(v, language, percent)))


def _parse_dates(periods) -> list[date] | None:
    """Period starts as dates, or None when any period is not an ISO date."""
    try:
        return [date.fromisoformat(str(p)[:10]) for p in periods]
    except ValueError:
        return None


def _date_axis(axis, language: str) -> None:
    """Year ticks ('2024') on long spans, month ticks ('Apr 2024') on short ones."""
    months = _MONTHS.get(language, _MONTHS["en"])

    def label(v, _pos):
        d = mdates.num2date(v)
        return str(d.year) if d.month == 1 and d.day == 1 else f"{months[d.month - 1]} {d.year}"

    axis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
    axis.set_major_formatter(FuncFormatter(label))


def _to_datauri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _new_chart(mode: str):
    """A figure on the theme's background with recessive axes: no box, a hairline
    baseline, solid hairline gridlines, secondary-ink tick labels."""
    theme = _THEMES.get(mode, _THEMES["light"])
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    fig.patch.set_facecolor(theme["bg"])
    ax.set_facecolor(theme["bg"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["grid"])
    ax.tick_params(colors=theme["muted"], labelsize=9, length=0, pad=6)
    ax.grid(True, color=theme["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax, theme


def _label_colors(ax, theme) -> None:
    ax.xaxis.label.set_color(theme["muted"])
    ax.yaxis.label.set_color(theme["muted"])


def trend_chart(periods, values, slope, intercept, unit: str = "", times=None,
                language: str = "tr", percent: bool = False, mode: str = "light") -> str:
    """*times*: each period's position (years since the first); evenly spaced when
    omitted. slope/intercept use the same unit (Sen's slope per year). The x axis
    is a real date axis when the periods are ISO dates. No title: the report's section
    heading sits right above the chart. *unit* labels the value axis ("people")."""
    legend = _LEGEND.get(language, _LEGEND["en"])
    fig, ax, theme = _new_chart(mode)
    t = list(times) if times is not None else list(range(len(values)))
    dates = _parse_dates(periods)
    x = dates if dates is not None else t
    if slope is not None and intercept is not None:
        line = [intercept + slope * i for i in t]
        ax.plot(x, line, color=theme["reference"], linestyle=(0, (4, 3)), linewidth=1.8,
                label=legend["trend"], zorder=2)
    # A dot on every period while they can be told apart; on a dense series only the
    # latest period gets one, so the line does not break up into dots.
    marks = None if len(values) <= 12 else [len(values) - 1]
    ax.plot(x, values, color=theme["series"], linewidth=2, solid_capstyle="round",
            solid_joinstyle="round", marker="o", markersize=6, markevery=marks,
            markeredgecolor=theme["bg"], markeredgewidth=1.5,
            label=legend["observed"], zorder=3)
    if slope is not None and intercept is not None:
        handles, names = ax.get_legend_handles_labels()
        ax.legend(handles[::-1], names[::-1], frameon=False, labelcolor=theme["text"],
                  fontsize=9, loc="best")
    if dates is not None:
        _date_axis(ax.xaxis, language)
    else:
        ax.set_xticks(x)
        ax.set_xticklabels([str(p) for p in periods])
    _value_axis(ax.yaxis, language, percent)
    ax.grid(False, axis="x")
    ax.set_ylabel(unit)
    _label_colors(ax, theme)
    return _to_datauri(fig)


def comparison_chart(labels, values, unit: str = "", language: str = "tr",
                     percent: bool = False, mode: str = "light") -> str:
    fig, ax, theme = _new_chart(mode)
    ax.bar(labels, values, color=theme["series"], width=0.6)
    _value_axis(ax.yaxis, language, percent)
    ax.grid(False, axis="x")
    ax.set_ylabel(unit)
    ax.tick_params(axis="x", rotation=45)
    _label_colors(ax, theme)
    return _to_datauri(fig)


def correlation_chart(x, y, xlabel: str, ylabel: str,
                      language: str = "tr", x_percent: bool = False,
                      y_percent: bool = False, mode: str = "light") -> str:
    fig, ax, theme = _new_chart(mode)
    ax.scatter(x, y, s=48, color=theme["series"], edgecolors=theme["bg"], linewidths=1.5,
               zorder=3)
    _value_axis(ax.xaxis, language, x_percent)
    _value_axis(ax.yaxis, language, y_percent)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _label_colors(ax, theme)
    return _to_datauri(fig)
