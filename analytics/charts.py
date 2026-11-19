"""Teknik izleme raporu için matplotlib grafikleri → base64 PNG data-URI.

Başsız Agg backend (import sırasında ayarlanır). Her fonksiyon rapora gömülebilir
'data:image/png;base64,...' döndürür (mevcut section_images formatı ile uyumlu).
Temiz stil: başlık, eksen etiketleri, ızgara.
"""
import base64
import io
import logging
import textwrap
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

logger = logging.getLogger(__name__)

_FIGSIZE = (8, 4.5)
_DPI = 120

# The app's colours, light and dark (frontend/src/style.css): page ground, text, muted
# text and hairline tokens. `series` is Chart Teal, the only hue that plots data.
# `reference` (the Sen trend line) is a neutral slate, dashed: an annotation of the series,
# not a second series, so it carries no hue of its own (dataviz validator: CVD separation
# from the teal 14.7 light / 12.4 dark, normal vision 17.3 / 18.2; the dash and the legend
# are its second encoding). `latest` is coral, used for the newest observation only.
_THEMES = {
    "light": {"bg": "#ffffff", "text": "#0b1d2e", "muted": "#56657a", "grid": "#e3e8ef",
              "series": "#0a8f88", "reference": "#44546a", "latest": "#d9452a"},
    "dark": {"bg": "#0b1d2e", "text": "#e8eef5", "muted": "#aebdcd", "grid": "#22394f",
             "series": "#16a196", "reference": "#aebdcd", "latest": "#e8553a"},
}

# Legend text in the report language (the report itself is "tr" or "en").
_LEGEND = {
    "tr": {"observed": "Gözlem", "trend": "Eğilim (Sen)"},
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
            scaled = value / limit
            # Three significant digits: 929K, 78.5K, 1.79M.
            decimals = 0 if abs(scaled) >= 100 else 1 if abs(scaled) >= 10 else 2
            return _number(scaled, language, decimals) + suffix
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


def _to_datauri(fig, source: str = "", theme: dict | None = None) -> str:
    """PNG data URI. *source* is printed under the chart, below the axis labels, wrapped
    so a long credit line (IOM DTM's, or two of them) does not widen the image."""
    if source:
        fig.text(0, 0, textwrap.fill(source, 130), ha="left", va="top", fontsize=8,
                 color=(theme or _THEMES["light"])["muted"])
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
                language: str = "tr", percent: bool = False, mode: str = "light",
                source: str = "", connect: bool = True) -> str:
    """*connect*: False draws the observations as separate points, with no line between
    them (years that are not comparable must not read as a movement).
    *times*: each period's position (years since the first); evenly spaced when
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
    ax.plot(x, values, color=theme["series"], linewidth=2 if connect else 0, solid_capstyle="round",
            solid_joinstyle="round", marker="o", markersize=6, markevery=marks,
            markeredgecolor=theme["bg"], markeredgewidth=1.5,
            label=legend["observed"], zorder=3)
    # The newest observation, and only it, in coral.
    ax.plot([x[-1]], [values[-1]], marker="o", markersize=7, linestyle="none",
            color=theme["latest"], markeredgecolor=theme["bg"], markeredgewidth=1.5, zorder=4)
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
    return _to_datauri(fig, source, theme)


_ROW_INCHES = 0.34     # one region per row; the figure grows with the region count
_BAR_PX = 22           # bar thickness (the dataviz cap is 24 px)
_END_PX = 4            # rounded data end


def comparison_chart(labels, values, language: str = "tr", percent: bool = False,
                     mode: str = "light", source: str = "") -> str:
    """Horizontal bars, largest first, region names left and each value at its bar's
    tip (so there is no value axis). The data end is rounded, the baseline square."""
    theme = _THEMES.get(mode, _THEMES["light"])
    order = sorted(zip(labels, values), key=lambda lv: lv[1], reverse=True)
    n = len(order)
    height = max(1.6, n * _ROW_INCHES + 0.4)
    fig, ax = plt.subplots(figsize=(_FIGSIZE[0], height))
    # Fixed margins in inches: the default fractions grow with the figure and left the
    # source line far below the last bar.
    fig.subplots_adjust(top=1 - 0.05 / height, bottom=0.3 / height)
    fig.patch.set_facecolor(theme["bg"])
    ax.set_facecolor(theme["bg"])
    for spine in ax.spines.values():
        spine.set_visible(False)

    top = max((v for _, v in order), default=0) or 1
    ax.set_xlim(0, top * 1.14)              # room for the value labels past the longest bar
    ax.set_ylim(n - 0.5, -0.5)              # first (largest) row at the top
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    x_per_px = (top * 1.14) / bbox.width
    y_per_px = n / bbox.height
    bar_h = _BAR_PX * y_per_px
    end_x = _END_PX * x_per_px

    for row, (_, value) in enumerate(order):
        if value <= 0:
            continue
        y0 = row - bar_h / 2
        # Rounded box, then a square block over its baseline end.
        ax.add_patch(FancyBboxPatch((0, y0), value, bar_h,
                                    boxstyle=f"round,pad=0,rounding_size={end_x}",
                                    mutation_aspect=y_per_px / x_per_px,
                                    facecolor=theme["series"], edgecolor="none"))
        ax.add_patch(Rectangle((0, y0), min(value, end_x * 1.5), bar_h,
                               facecolor=theme["series"], edgecolor="none"))
        ax.text(value + 6 * x_per_px, row, format_value(value, language, percent),
                va="center", ha="left", fontsize=9, color=theme["text"])

    ax.set_yticks(range(n))
    ax.set_yticklabels([label for label, _ in order])
    ax.tick_params(axis="y", colors=theme["muted"], labelsize=9, length=0, pad=8)
    ax.set_xticks([])
    return _to_datauri(fig, source, theme)


def correlation_chart(x, y, xlabel: str, ylabel: str,
                      language: str = "tr", x_percent: bool = False,
                      y_percent: bool = False, mode: str = "light",
                      source: str = "") -> str:
    fig, ax, theme = _new_chart(mode)
    ax.scatter(x, y, s=48, color=theme["series"], edgecolors=theme["bg"], linewidths=1.5,
               zorder=3)
    _value_axis(ax.xaxis, language, x_percent)
    _value_axis(ax.yaxis, language, y_percent)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _label_colors(ax, theme)
    return _to_datauri(fig, source, theme)
