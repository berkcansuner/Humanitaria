"""The technical report's own text, written in code in the report's language.

Every sentence of a technical monitoring report (values, dates, directions, test results,
verdicts, caveats, data gaps, methods) is built here from the computed findings, in
English or Turkish: no model writes or rewords any of it, so every statement traces to an
HDX HAPI dataset in the report's source list.

No sentence is joined by a semicolon (an owner rule for all visible text, 2026-11-19).

Turkish sentences keep figures and dates out of case-suffix positions ("Son değer 17,4
milyon kişi (2026)"), so no vowel harmony is ever computed.
"""
import re
from datetime import date

from analytics import technical_report as tr
from analytics.stat_tests import CORRELATION_MIN_POINTS

HEADINGS = {
    "en": {"summary": "Executive Summary", "coverage": "Data Coverage & Limitations",
           "methods": "Methods"},
    "tr": {"summary": "Yönetici Özeti", "coverage": "Veri Kapsamı ve Sınırlılıklar",
           "methods": "Yöntem"},
}

_SWAP = str.maketrans(",.", ".,")
_FIGURE = re.compile(r"\d[\d.,]*\d|\d")
_UNITS = {"en": {"people": "people", "USD": "USD"}, "tr": {"people": "kişi", "USD": "ABD doları"}}
_COUNT_TR = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on",
             "on bir", "on iki"]


def _lang(language: str) -> str:
    return "tr" if language == "tr" else "en"


def _loc(text: str, lang: str) -> str:
    """Figures written the English way, in the language's format (17.4 -> 17,4)."""
    return _FIGURE.sub(lambda m: m.group(0).translate(_SWAP), text) if lang == "tr" else text


def _amount(value: float, unit: str, lang: str, exact: bool = False) -> str:
    """'17.4 million people' / '17,4 milyon kişi', '32.0%' / '%32,0'. In full when exact."""
    if unit == "%":
        n = _loc(tr._plain(value), lang)
        return f"%{n}" if lang == "tr" else f"{n}%"
    word = _UNITS[lang].get(unit, unit)
    if exact:
        return f"{_loc(tr._full(value), lang)} {word}"
    body = tr._amount(value, "").strip()
    if lang == "tr":
        body = (_loc(body, lang).replace("million", "milyon").replace("billion", "milyar")
                .replace("about", "yaklaşık"))
    return f"{body} {word}"


def _amounts(values: list, unit: str, lang: str, exact: bool = False) -> list[str]:
    """As the findings write them: in full when two values would round alike."""
    full = unit != "%" and (exact or len({tr._amount(v, unit) for v in values}) < len(set(values)))
    return [_amount(v, unit, lang, exact=full) for v in values]


def _rate(value: float, r: dict, lang: str) -> str:
    if r.get("unit") == "percentage points":
        return f"{_loc(tr._plain(value), lang)} {'yüzde puan' if lang == 'tr' else 'percentage points'}"
    return _amount(value, r.get("value_unit") or "people", lang)


def _when(period, resolution: str, lang: str) -> str:
    d = date.fromisoformat(str(period)[:10])
    return str(d.year) if resolution == "year" else f"{tr._MONTH_NAMES[lang][d.month - 1]} {d.year}"


def _day(iso: str, lang: str) -> str:
    d = date.fromisoformat(str(iso)[:10])
    return f"{d.day} {tr._MONTH_NAMES[lang][d.month - 1]} {d.year}"


def _count(n: int, lang: str) -> str:
    words = _COUNT_TR if lang == "tr" else tr._NUMBER_WORDS
    return words[n] if 0 <= n < len(words) else str(n)


def _signed(value: float, lang: str) -> str:
    return _loc(f"{value:+.1f}", lang)


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _verdict(r: dict, test: str, subject: str, lang: str) -> str:
    """The test's p-value(s) and the code's verdict."""
    p = _loc(tr._fmt_p(r["p_value"]), lang)
    holm = r.get("family", 2) >= 2
    if lang == "tr":
        adjusted = f" (Holm düzeltmeli {_loc(tr._fmt_p(r['p_adjusted']), lang)})" if holm else ""
        return (f"{test} {p} veriyor{adjusted}. {_cap(subject)} 0,05 düzeyinde istatistiksel olarak "
                f"anlamlı{'' if r['significant'] else ' değil'}.")
    adjusted = f" (Holm-adjusted {tr._fmt_p(r['p_adjusted'])})" if holm else ""
    return (f"{test} gives {p}{adjusted}, so {subject} is "
            f"{'' if r['significant'] else 'not '}statistically significant at the 0.05 level.")


def _before(r: dict, lang: str) -> str:
    lb = r.get("look_back")
    if not (lb and not lb["chosen_points"]):
        return ""
    return ", seçilen dönemden önce" if lang == "tr" else ", before the chosen period"


def _turn(r: dict, lang: str) -> str:
    """When the latest value sits on the other side of the first value than the trend
    points (a series that peaked or bottomed out inside the window), the sentence that
    says so, with the extreme value. Otherwise ''. Without it "latest 8.59 million, first
    7.07 million, decreasing" reads as a contradiction."""
    values, periods = r.get("values"), r.get("periods")
    falling = r["direction"] == "decreasing"
    if not values or r["direction"] not in ("increasing", "decreasing") or \
            (r["latest_value"] > r["first_value"]) != falling or r["latest_value"] == r["first_value"]:
        return ""
    extreme = max(values) if falling else min(values)
    when = _when(periods[values.index(extreme)], r.get("resolution", "month"), lang)
    shown = _amount(extreme, r["value_unit"], lang)
    if lang == "tr":
        return (f"Son değer ilk değerin {'üzerinde' if falling else 'altında'} olsa da pencerenin "
                f"tamamındaki eğilim {'azalış' if falling else 'artış'} yönünde. Serinin en "
                f"{'yüksek' if falling else 'düşük'} değeri {shown} ({when}). ")
    return (f"The latest value is {'above' if falling else 'below'} the first, while the trend "
            f"over the whole window is {'decreasing' if falling else 'increasing'}: the series' "
            f"{'highest' if falling else 'lowest'} value is {shown} ({when}). ")


def _trend(r: dict, lang: str) -> str:
    res, unit = r.get("resolution", "month"), r["value_unit"]
    first, last = _when(r["first_period"], res, lang), _when(r["last_period"], res, lang)
    latest, start = _amount(r["latest_value"], unit, lang), _amount(r["first_value"], unit, lang)
    slope = _rate(r["slope"], r, lang)
    tau = _loc(f"{r['tau']:.2f}", lang)
    n = _count(r["n_points"], lang)
    if lang == "tr":
        window = (f"Geriye bakış penceresinde ({first} – {last})" if r.get("look_back")
                  else f"{first} – {last} arasında")
        direction = {"increasing": "eğilim artış yönünde", "decreasing": "eğilim azalış yönünde"}.get(
            r["direction"], "tek yönlü bir eğilim yok")
        ci = ("hesaplamak için nokta sayısı yetersiz" if r["ci_low"] is None
              else f"{_rate(r['ci_low'], r, lang)} ile {_rate(r['ci_high'], r, lang)} arası")
        text = (f"Son değer {latest} ({last}{_before(r, lang)}). Penceredeki ilk değer {start} "
                f"({first}). {window} {direction}: Sen eğimi yılda {slope} (%95 güven aralığı: "
                f"{ci}), Kendall tau {tau}. " + _turn(r, lang)
                + _verdict(r, "Mann-Kendall testi", "eğilim", lang))
        if r.get("line_change") is not None:
            text += f" Eğilim çizgisi boyunca değişim {_signed(r['line_change'], lang)} yüzde puan."
        elif r["pct_change"] is not None:
            sign = "-" if r["pct_change"] < 0 else "+"
            text += (f" Eğilim çizgisi boyunca göreli değişim "
                     f"{sign}%{_loc(f'{abs(r['pct_change']):.1f}', lang)}.")
        return text + f" Seride {n} gözlem var."
    window = (f"Over the look-back window, {first} to {last}," if r.get("look_back")
              else f"From {first} to {last},")
    direction = {"increasing": "the trend is increasing", "decreasing": "the trend is decreasing"}.get(
        r["direction"], "there is no monotonic trend")
    ci = ("too few points to compute" if r["ci_low"] is None
          else f"{_rate(r['ci_low'], r, lang)} to {_rate(r['ci_high'], r, lang)}")
    text = (f"The latest value is {latest} ({last}{_before(r, lang)}). The first value in the "
            f"window is {start} ({first}). {window} {direction}: Sen's slope is {slope} per year "
            f"(95% confidence interval: {ci}), and Kendall's tau is {tau}. " + _turn(r, lang)
            + _verdict(r, "The Mann-Kendall test", "the trend", lang))
    if r.get("line_change") is not None:
        text += f" The change along the trend line is {_signed(r['line_change'], lang)} percentage points."
    elif r["pct_change"] is not None:
        text += f" The relative change along the trend line is {r['pct_change']:+.1f}%."
    return text + f" The series has {n} observations."


# Why a series' years are not comparable, one sentence per kind of year.
_NOT_COMPARABLE = {
    "tr": {"below": "planın ayrı “{s}” satırlarından biri, genel rakam değil",
           "line": "planın genel rakamı yerine ayrı “{s}” satırlarından biri olabilir",
           "single": "planın tek “{s}” rakamı",
           "open": "Değerler yıllar arasında karşılaştırılamaz.",
           "which": "HDX HAPI her yılın rakamının hangi satır olduğunu belirtmiyor.",
           "plain": "Yıllar farklı bir temelde raporlandı.",
           "close": "Bu nedenle eğilim testi yapılmadı."},
    "en": {"below": "one of the plan's separate {s} lines, not its overall figure",
           "line": "possibly one of the plan's separate {s} lines rather than its overall figure",
           "single": "the plan's only {s} figure",
           "open": "The values are not comparable across years.",
           "which": "HDX HAPI does not say which line each year's figure is.",
           "plain": "The years are reported on a different basis.",
           "close": "No trend is tested."},
}


def _not_comparable(r: dict, lang: str) -> str:
    words = _NOT_COMPARABLE[lang]
    years = r.get("not_comparable_years")
    if not years:
        return f"{words['open']} {words['plain']} {words['close']}"
    sector = r.get(f"sector_{lang}") or ("sektör" if lang == "tr" else "sector")
    parts = [f"{', '.join(ys)}: {words[kind].format(s=sector)}." for kind, ys in years.items()]
    return " ".join([words["open"], *parts, words["which"], words["close"]])


def _snapshot(r: dict, lang: str) -> str:
    res, unit = r.get("resolution", "month"), r["value_unit"]
    points = list(zip(r["periods"], r["values"]))
    n = len(points)
    shown = _amounts([v for _, v in points], unit, lang, r.get("exact", False))
    dated = [f"{a} ({_when(p, res, lang)})" for (p, _), a in zip(points, shown)]
    lb = r.get("look_back")
    tr_ = lang == "tr"
    opening = (("Geriye bakış penceresinde son değer" if lb else "Son değer") if tr_
               else ("In the look-back window, the latest value is" if lb else "The latest value is"))
    text = f"{opening} {shown[-1]} ({_when(points[-1][0], res, lang)}{_before(r, lang)})"
    earlier = dated[:-1]
    if n > 1 and not r.get("not_comparable"):
        lv, pv = points[-1][1], points[-2][1]
        previous = f"{shown[-2]}, {_when(points[-2][0], res, lang)}"
        if tr_:
            text += (f", bir önceki değerle ({previous}) aynı" if lv == pv else
                     f", bir önceki değerin ({previous}) {'üzerinde' if lv > pv else 'altında'}")
        else:
            move = "up from" if lv > pv else ("down from" if lv < pv else "the same as")
            text += f", {move} {shown[-2]} in {_when(points[-2][0], res, lang)}"
        earlier = dated[:-2]
    text += "."
    if earlier:
        label = (("Daha önceki değer" if len(earlier) == 1 else "Daha önceki değerler") if tr_
                 else ("Earlier value" if len(earlier) == 1 else "Earlier values"))
        text += f" {label}: {', '.join(reversed(earlier))}."
    if r.get("not_comparable"):
        return f"{text} {_not_comparable(r, lang)}"
    if n >= r["min_points"]:
        return text + (" Değerler değişmediği için eğilim testi yapılmadı." if tr_
                       else " The values do not vary, so no trend is tested.")
    count = _cap(_count(n, lang))
    if tr_:
        return text + f" {count} gözlem eğilim testi için yetersiz."
    return text + (" One observation is too few for a trend test." if n == 1
                   else f" {count} observations are too few for a trend test.")


def _region(r: dict, lang: str) -> str:
    unit, res = r.get("value_unit", "people"), r.get("resolution", "month")
    top = ", ".join(f"{name} ({_amount(val, unit, lang)})" for name, val in r["ranking"][:3])
    first, last = _when(r["first_period"], res, lang), _when(r["last_period"], res, lang)
    tr_ = lang == "tr"
    if tr_:
        when = (f"({first} itibarıyla)" if first == last
                else f"(bölge başına ortalama, {first} – {last})")
        text = f"En yüksek bölgeler {when}: {top}."
    else:
        when = f"as of {first}" if first == last else f"(mean per region, {first} to {last})"
        text = f"Highest regions {when}: {top}."
    if r["p_value"] is None:
        one = r["max_obs"] <= 1
        if tr_:
            why = ("her bölge için tek gözlem var" if one
                   else "iki veya daha fazla gözlemi olan bölge sayısı ikiden az")
            return text + f" Bölgeler arasında istatistiksel karşılaştırma yapılamadı: {why}."
        why = ("one observation per region" if one
               else "fewer than two regions have two or more observations")
        return text + f" A statistical comparison between regions was not possible: {why}."
    h = "n/a" if r["kruskal_h"] is None else _loc(f"{r['kruskal_h']:.2f}", lang)
    if tr_:
        return text + " " + _verdict(r, f"Bölgeler arasındaki fark için Kruskal-Wallis testi H={h},",
                                     "fark", lang)
    return text + " " + _verdict(r, f"The Kruskal-Wallis test of the difference between regions "
                                    f"(H={h})", "the difference", lang)


def _correlation(r: dict, lang: str) -> str:
    coef = "n/a" if r["coefficient"] is None else _loc(f"{r['coefficient']:.2f}", lang)
    n = _count(r["n_points"], lang)
    method = str(r["method"]).capitalize()
    if lang == "tr":
        return (f"{r['indicator_x']} ile {r['indicator_y']} arasındaki {method} korelasyonu: "
                f"r={coef} ({n} ortak dönem). " + _verdict(r, "Test", "korelasyon", lang))
    return (f"{method} correlation between {r['indicator_x']} and {r['indicator_y']}: r={coef} "
            f"over {n} common periods. " + _verdict(r, "The test", "the correlation", lang))


_FACTS = {"trend": _trend, "snapshot": _snapshot, "region": _region, "correlation": _correlation}


def section_facts(stat_result: dict, language: str) -> str:
    """One finding's paragraph: everything the code computed about it."""
    return _FACTS[stat_result["kind"]](stat_result, _lang(language))


def _headline(item: dict, lang: str) -> str:
    """A sector's own figure with its date and, as sentences of their own, its caveats."""
    figure = _amount(item["value"], item["unit"], lang, exact=item["exact"])
    tr_ = lang == "tr"
    before = (", seçilen dönemden önce" if tr_ else ", before the chosen period") if item["before"] else ""
    sector = item.get(f"sector_{lang}") or ("sektör" if tr_ else "sector")
    out = [f"{item['name']}: {figure} ({_when(item['period'], item['resolution'], lang)}{before})."]
    if item["not_comparable"]:
        out.append("Önceki yıllar farklı bir temelde raporlandığı için karşılaştırılamaz." if tr_
                   else "Earlier years are reported on a different basis and are not comparable.")
    if item["caveat"] == "not_overall":
        out.append(f"Bu rakam planın genel “{sector}” rakamı değil." if tr_
                   else f"This figure is not the plan's overall {sector} figure.")
    elif item["caveat"] == "maybe_not_overall":
        out.append(f"Bu rakam planın genel “{sector}” rakamı olmayabilir." if tr_
                   else f"This figure may not be the plan's overall {sector} figure.")
    return " ".join(out)


def _latest_values(findings, lang: str) -> list[str]:
    """'name: value (date)' for each series the report shows, except a sector's own
    figures (the headline gives those, with their caveats)."""
    in_headline = {item["name"] for item in findings.headline_items}
    out = {}
    for s in findings.sections:
        r = s.stat_result
        if r["kind"] not in ("trend", "snapshot") or r["indicator"] in in_headline:
            continue
        if r["kind"] == "trend":
            value, period = r["latest_value"], r["latest_period"]
            shown = _amount(value, r["value_unit"], lang)
        else:
            period = r["periods"][-1]
            shown = _amounts(r["values"], r["value_unit"], lang, r.get("exact", False))[-1]
        when = _when(period, r.get("resolution", "month"), lang)
        out[r["indicator"]] = f"{r['indicator']}: {shown} ({when}{_before(r, lang)})"
    return list(out.values())


def _tested(findings) -> list:
    return [s for s in findings.sections if s.stat_result.get("p_value") is not None]


def _bullets(items: list[str], stop: bool = True) -> str:
    """A markdown list. Every item ends with a full stop, except a list of names
    (*stop* False: section headings)."""
    return "\n".join(f"- {i.rstrip('.')}{'.' if stop else ''}" for i in items)


def summary_facts(findings, language: str) -> str:
    """The Executive Summary: the period, the latest figures as a list (a sector's own
    first, with their caveats), what the tests found, the look-back and the limitation."""
    lang = _lang(language)
    tr_ = lang == "tr"
    blocks = []
    if findings.date_from:
        span = (f"{_day(findings.date_from, lang)} – {_day(findings.date_to, lang)}" if tr_
                else f"{_day(findings.date_from, lang)} to {_day(findings.date_to, lang)}")
        if findings.default_years:
            years = _count(findings.default_years, lang)
            span += (f" (dönem seçilmedi: son {years} yıl)" if tr_
                     else f" (no period was chosen: the last {years} years)")
        blocks.append(f"{'Analiz edilen dönem' if tr_ else 'Period analysed'}: {span}.")
    figures = [_headline(item, lang) for item in findings.headline_items] + _latest_values(findings, lang)
    if figures:
        blocks.append(f"{'Son değerler' if tr_ else 'Latest values'}:\n\n{_bullets(figures)}")

    tested = _tested(findings)
    significant = [s.heading for s in tested if s.stat_result["significant"]]
    if tr_:
        after = " Holm düzeltmesinden sonra" if len(tested) >= 2 else ""
    else:
        after = " after the Holm correction" if len(tested) >= 2 else ""
    closing = []
    if not tested:
        closing.append("İstatistiksel test yapılamadı. Bulgular gözlenen değerleriyle raporlanıyor." if tr_
                       else "No statistical test was possible. The findings are reported as their "
                            "observed values.")
    elif len(tested) == 1:
        heading = tested[0].heading
        if tr_:
            closing.append(f"Bu raporda bir istatistiksel test yapıldı ({heading}). Sonuç 0,05 "
                           f"düzeyinde istatistiksel olarak anlamlı{'' if significant else ' değil'}.")
        else:
            closing.append(f"This report ran one statistical test ({heading}). Its result is "
                           f"{'' if significant else 'not '}statistically significant at the 0.05 level.")
    else:
        n = _count(len(tested), lang)
        ran = (f"Bu raporda {n} istatistiksel test yapıldı." if tr_
               else f"This report ran {n} statistical tests.")
        if significant:
            lead = (f"{ran} 0,05 düzeyinde{after} istatistiksel olarak anlamlı olanlar:" if tr_
                    else f"{ran} These are statistically significant at the 0.05 level{after}:")
            blocks.append(f"{lead}\n\n{_bullets(significant, stop=False)}")
        elif tr_:
            closing.append(f"{ran} {'İkisi de' if len(tested) == 2 else 'Hiçbiri'} 0,05 düzeyinde"
                           f"{after} istatistiksel olarak anlamlı değil.")
        else:
            closing.append(f"{ran} {'Neither' if len(tested) == 2 else 'None'} is statistically "
                           f"significant at the 0.05 level{after}.")
    looked = [s.stat_result for s in findings.sections if s.stat_result.get("look_back")]
    if looked:
        names = ", ".join(dict.fromkeys(r["indicator"] for r in looked))
        lb = looked[0]["look_back"]
        if tr_:
            closing.append(f"Seçilen dönemdeki gözlem sayısı şu göstergeler için yetersiz: {names}. "
                           f"Bu göstergelerin değerleri ve eğilimleri daha uzun geriye bakış "
                           f"penceresini kapsıyor ({_day(lb['date_from'], lang)} – "
                           f"{_day(lb['date_to'], lang)}).")
        else:
            closing.append(f"The chosen period holds too few observations for {names}, so their "
                           f"values and trends cover the longer look-back window "
                           f"{_day(lb['date_from'], lang)} to {_day(lb['date_to'], lang)}.")
    closing.append(_limitation(findings, lang, short=True))
    blocks.append(" ".join(closing))
    return "\n\n".join(blocks)


_LONG_SERIES = 12     # from this many observations a series is not called short


def _limitation(findings, lang: str, short: bool = False) -> str:
    tested = bool(_tested(findings))
    # "The series are short" is not said of a 40-observation series.
    some_long = any(s.stat_result.get("n_points", 0) >= _LONG_SERIES for s in findings.sections
                    if s.stat_result["kind"] == "trend")
    if lang == "tr":
        series = "Serilerin çoğu kısa" if some_long else "Seriler kısa"
        if not tested:
            return f"{series} olduğundan değerler betimleyicidir."
        if short:
            return f"{series} olduğundan sonuçlar gösterge niteliğindedir."
        return (f"{series}dır. Testler gözlemlerin bağımsız olduğunu varsayar ve ardışık dönemler "
                "arasındaki seri korelasyon düzeltilmez. Bu nedenle sonuçlar gösterge "
                "niteliğindedir.")
    series = "Most of the series are short" if some_long else "The series are short"
    if not tested:
        return f"{series}, so the values are descriptive."
    if short:
        return f"{series}, so the results are indicative."
    return (f"{series}. The tests assume independent observations, and serial correlation "
            "between consecutive periods is not corrected for, so the results are indicative.")


_GAPS = {
    "tr": {"not_retrieved": "HDX HAPI'den alınamadı",
           "no_data": "dönemde veri yok",
           "too_few": "eğilim testi için gözlem sayısı yetersiz (n={n})",
           "flat": "değerler {n} gözlem boyunca değişmediği için eğilim testi yapılmadı",
           "not_comparable": "yıllar karşılaştırılabilir olmadığından eğilim testi yapılmadı",
           "analysis_error": "analiz hatası"},
    "en": {"not_retrieved": "could not be retrieved from HDX HAPI",
           "no_data": "no data in the period",
           "too_few": "too few observations for a trend test (n={n})",
           "flat": "the values do not vary across {n} observations, so no trend was tested",
           "not_comparable": "years not comparable, so no trend was tested",
           "analysis_error": "analysis error"},
}
_WINDOW = {"tr": {"chosen": " (seçilen dönem)", "look_back": " (geriye bakış penceresi)", None: ""},
           "en": {"chosen": " (chosen period)", "look_back": " (look-back window)", None: ""}}


def _full(value: float, lang: str) -> str:
    return _loc(tr._full(value), lang)


def _note(item: dict, lang: str) -> str:
    """One data note, from its data: what a series leaves out or cannot say."""
    kind, name, tr_ = item["kind"], item["name"], lang == "tr"
    if kind == "plan_line":
        sector = item[f"sector_{lang}"]
        listed = ", ".join(f"{n} {_full(v, lang)}" for n, v in item["lines"])
        figure = _full(item["figure"], lang)
        if tr_:
            what = (f"Bu rakam ({figure}) bu satırlardan birinin altında olduğundan planın genel "
                    f"“{sector}” rakamı değil. HDX HAPI bunun planın hangi satırı olduğunu "
                    f"belirtmiyor." if item["below"] else
                    f"Bu rakam ({figure}), planın genel “{sector}” rakamı yerine (HDX HAPI'de "
                    f"listelenmeyen) başka bir “{sector}” satırı olabilir.")
            return (f"{name}, {item['year']}: plan “{sector}” başlığını ayrı satırlarda raporluyor "
                    f"({listed}). {what} Kişiler birden fazla satırda sayılabildiği için bu raporda "
                    f"satırlar toplanmadı.")
        what = (f"This figure ({figure}) is below one of them, so it is not the plan's overall "
                f"{sector} figure. HDX HAPI does not say which of the plan's lines it is."
                if item["below"] else
                f"This figure ({figure}) may be another of the plan's {sector} lines (not listed "
                f"in HDX HAPI) rather than its overall {sector} figure.")
        return (f"{name}, {item['year']}: the plan reports {sector} in separate lines ({listed}). "
                f"{what} This report does not add the lines up, because people can be counted in "
                f"more than one.")
    prefix = f"{name}{_WINDOW[lang][item.get('window')]}: "
    if kind == "dtm":
        ops, rounds = item["other_operations"], item["incomplete_rounds"]
        if tr_:
            parts = [f"Yalnızca “{item['operation']}” adlı DTM operasyonu kullanıldı."]
            if ops:
                parts.append(f"Yerinden edilmeyi farklı sayan {ops} başka operasyon karıştırılmadı.")
            if rounds:
                parts.append(f"Bölgelerinin %80'inden azını kapsayan {rounds} eksik tur dışarıda "
                             f"bırakıldı.")
        else:
            parts = [f"Only the DTM operation “{item['operation']}” is used."]
            if ops:
                parts.append(f"{_cap(_count(ops, lang))} other operation"
                             f"{' counts' if ops == 1 else 's count'} "
                             f"displacement differently and {'is' if ops == 1 else 'are'} not mixed in.")
            if rounds:
                parts.append(f"{_cap(_count(rounds, lang))} incomplete round"
                             f"{'' if rounds == 1 else 's'} covering under "
                             f"80% of its regions {'is' if rounds == 1 else 'are'} left out.")
        return prefix + " ".join(parts)
    if kind == "ipc":
        low, high = (_loc(f"{v / 1e6:.1f}", lang) for v in (item["low"], item["high"]))
        if tr_:
            return (f"{prefix}IPC analizleri farklı dönemlerde ülkenin farklı bölümlerini kapsadı "
                    f"(analiz edilen nüfus {low} – {high} milyon). Bu nedenle kişi sayısı değil, "
                    f"analiz edilen nüfus içindeki pay kullanıldı.")
        return (f"{prefix}IPC analyses covered different parts of the country in different periods "
                f"(analysed population {low} to {high} million), so the share of the analysed "
                f"population is used, not the number of people.")
    parts = []
    for t in item["years"]:
        blank, total = _full(t["blank"], lang), _full(t["total"], lang)
        if tr_:
            parts.append(f"HDX HAPI {t['year']} için iki toplam içeriyor: kırılımsız {blank}"
                         + (" (kullanılan)" if t["used"] == "" else "")
                         + f" ve kırılım toplamı {total}" + (" (kullanılan)" if t["used"] == "total" else "")
                         + ".")
        else:
            parts.append(f"HDX HAPI holds two totals for {t['year']}: {blank} without a breakdown"
                         + (" (used)" if t["used"] == "" else "")
                         + f" and {total} as the total of its breakdown"
                         + (" (used)" if t["used"] == "total" else "") + ".")
    parts.append("HNO'nun yayımladığı sektör rakamı farklı olabilir." if tr_
                 else "The HNO's published sector figure may differ.")
    return prefix + " ".join(parts)


def coverage_text(findings, language: str) -> str:
    """Data Coverage & Limitations: the gaps, what each series leaves out, the limitation."""
    lang = _lang(language)
    # A series whose years are not comparable gives that as its reason here too, not
    # "too few observations" (its finding says "not comparable … no trend is tested").
    not_comparable = {s.stat_result["indicator"] for s in findings.sections
                      if s.stat_result.get("not_comparable")}
    gaps = [f"{g['name']}: " + _GAPS[lang]["not_comparable" if g["name"] in not_comparable
                                         else g["code"]].format(n=g.get("n"))
            for g in findings.gap_items]
    notes = [_note(n, lang) for n in findings.note_items]
    labels = (("Veri boşlukları:", "Veri notları:", "Sınırlılık:") if lang == "tr"
              else ("Data gaps:", "Data notes:", "Limitation:"))
    out = [f"{label}\n\n{_bullets(items)}" for label, items in zip(labels, (gaps, notes)) if items]
    limitation = _limitation(findings, lang)
    out.append(f"{labels[2]} {limitation[0].lower()}{limitation[1:]}")
    return "\n\n".join(out)


def methods_text(findings, language: str) -> str:
    """The methods this report used (and only those), and who wrote what."""
    lang = _lang(language)
    tr_ = lang == "tr"
    kinds = [s.stat_result["kind"] for s in _tested(findings)]
    out = []
    if not kinds:
        out.append("İstatistiksel test yapılamadı: her bulgu gözlenen değerleriyle raporlandı." if tr_
                   else "No statistical test was possible: every finding is reported as its "
                        "observed values.")
    if "trend" in kinds:
        out.append("Eğilim: Mann-Kendall testi. Eğim, dönemlerin gerçek tarihleri üzerinden yıl "
                   "başına Sen eğimidir, etki büyüklüğü de Kendall tau'dur." if tr_ else
                   "Trend: Mann-Kendall test. The slope is Sen's slope per year on the real dates "
                   "of the periods, and Kendall's tau is the effect size.")
    if "region" in kinds:
        out.append("Bölgeler: birinci düzey idari bölgeler (admin-1) arasında Kruskal-Wallis testi."
                   if tr_ else "Regions: Kruskal-Wallis test across admin-1 regions.")
    if "correlation" in kinds:
        out.append(f"Korelasyon: en az {CORRELATION_MIN_POINTS} ortak dönemi olan gösterge "
                   f"çiftleri için Pearson korelasyonu." if tr_ else
                   f"Correlation: Pearson, for indicator pairs with at least "
                   f"{CORRELATION_MIN_POINTS} common periods.")
    if len(kinds) >= 2:
        n = _count(len(kinds), lang)
        every = "her iki teste" if len(kinds) == 2 else f"{n} testin tümüne"
        out.append(f"Çoklu karşılaştırma: bu rapordaki {every} birlikte Holm düzeltmesi "
                   f"uygulandı. Anlamlılık 0,05 düzeyinde Holm düzeltmeli p-değerine göre "
                   f"belirlendi." if tr_ else
                   f"Multiple comparisons: Holm correction across "
                   f"{'both' if len(kinds) == 2 else f'all {n}'} tests in this report. "
                   f"Significance is decided on the Holm-adjusted p-value at the 0.05 level.")
    elif kinds:
        out.append("Tek bir istatistiksel test yapıldığı için çoklu karşılaştırma düzeltmesi "
                   "uygulanmadı. Anlamlılık 0,05 düzeyinde testin p-değerine göre belirlendi."
                   if tr_ else
                   "One statistical test was run, so no multiple-comparison correction applies. "
                   "Significance is decided on its p-value at the 0.05 level.")
    if tr_:
        out.append("Veriler HDX HAPI'den (Humanitarian Data Exchange'in veri API'si) alındı, "
                   "kullanılan veri setleri kaynak listesindedir. Bu rapordaki değerler, testler "
                   "ve sonuçlar kodla hesaplandı ve metin koddan üretildi. "
                   "Hiçbir bölümü yapay zekâ modeli yazmadı.")
    else:
        out.append("The data come from HDX HAPI (the Humanitarian Data Exchange's data API), and "
                   "the datasets used are in the source list. The values, tests and verdicts in "
                   "this report are computed in code, and its text is generated from them in code. "
                   "No part of it is written by an AI model.")
    return " ".join(out)


def opening(findings, language: str) -> str:
    """The report's first block."""
    return f"## {HEADINGS[_lang(language)]['summary']}\n\n{summary_facts(findings, language)}"


def section_block(section, language: str) -> str:
    return f"## {section.heading}\n\n{section_facts(section.stat_result, language)}"


def closing(findings, language: str) -> str:
    """Data Coverage & Limitations and Methods."""
    h = HEADINGS[_lang(language)]
    return (f"## {h['coverage']}\n\n{coverage_text(findings, language)}\n\n"
            f"## {h['methods']}\n\n{methods_text(findings, language)}")


def assemble(findings, language: str) -> str:
    """The whole report."""
    parts = [opening(findings, language)]
    parts += [section_block(s, language) for s in findings.sections]
    parts.append(closing(findings, language))
    return "\n\n".join(parts)
