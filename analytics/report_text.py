"""The technical report's own text, written in code in the report's language.

Every sentence of a technical monitoring report (values, dates, directions, test results,
verdicts, caveats, data gaps, methods) is built here from the computed findings, in
English or Turkish: no model writes or rewords any of it, so every statement traces to an
HDX HAPI dataset in the report's source list. The one exception is the "What changed"
section a next-period report adds, which a model writes and analytics.narrative_check and
rag.report_compare check; the Methods say so when it is there.

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
    """'17.4 million people' / '17,4 milyon kişi'; '32.0%' / '%32,0'; in full when exact."""
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


def _verdict(r: dict, test: str, subject: str, lang: str) -> str:
    """The test's p-value(s) and the code's verdict, as one sentence."""
    p = _loc(tr._fmt_p(r["p_value"]), lang)
    holm = r.get("family", 2) >= 2
    if lang == "tr":
        adjusted = f" (Holm düzeltmeli {_loc(tr._fmt_p(r['p_adjusted']), lang)})" if holm else ""
        return (f"{test} {p} veriyor{adjusted}; {subject} 0,05 düzeyinde istatistiksel olarak "
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
    says so, with the extreme value; else ''. Without it "latest 8.59 million, first 7.07
    million, decreasing" reads as a contradiction."""
    values, periods = r.get("values"), r.get("periods")
    falling = r["direction"] == "decreasing"
    if not values or r["direction"] not in ("increasing", "decreasing") or             (r["latest_value"] > r["first_value"]) != falling or r["latest_value"] == r["first_value"]:
        return ""
    extreme = max(values) if falling else min(values)
    when = _when(periods[values.index(extreme)], r.get("resolution", "month"), lang)
    shown = _amount(extreme, r["value_unit"], lang)
    if lang == "tr":
        return (f"Son değer ilk değerin {'üzerinde' if falling else 'altında'} olsa da pencerenin "
                f"tamamındaki eğilim {'azalış' if falling else 'artış'} yönünde; serinin en "
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
        text = (f"Son değer {latest} ({last}{_before(r, lang)}); penceredeki ilk değer {start} "
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
    text = (f"The latest value is {latest} ({last}{_before(r, lang)}); the first value in the "
            f"window is {start} ({first}). {window} {direction}: Sen's slope is {slope} per year "
            f"(95% confidence interval: {ci}), and Kendall's tau is {tau}. " + _turn(r, lang)
            + _verdict(r, "The Mann-Kendall test", "the trend", lang))
    if r.get("line_change") is not None:
        text += f" The change along the trend line is {_signed(r['line_change'], lang)} percentage points."
    elif r["pct_change"] is not None:
        text += f" The relative change along the trend line is {r['pct_change']:+.1f}%."
    return text + f" The series has {n} observations."


_NOT_COMPARABLE_TR = {
    "below": "planın ayrı “{s}” satırlarından biri, genel rakam değil",
    "line": "planın genel rakamı yerine ayrı “{s}” satırlarından biri olabilir",
    "single": "planın tek “{s}” rakamı",
}


def _not_comparable_tr(r: dict) -> str:
    years = r.get("not_comparable_years")
    if not years:
        return "yıllar farklı bir temelde raporlandı"
    sector = r.get("sector_tr") or "sektör"
    parts = [f"{', '.join(ys)}: {_NOT_COMPARABLE_TR[kind].format(s=sector)}"
             for kind, ys in years.items()]
    return "; ".join(parts) + "; HDX HAPI her yılın rakamının hangi satır olduğunu belirtmiyor"


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
        if tr_:
            text += (f"; bir önceki değerle ({shown[-2]}, {_when(points[-2][0], res, lang)}) aynı"
                     if lv == pv else
                     f"; bir önceki değerin ({shown[-2]}, {_when(points[-2][0], res, lang)}) "
                     f"{'üzerinde' if lv > pv else 'altında'}")
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
        return text + (
            f" Değerler yıllar arasında karşılaştırılamaz ({_not_comparable_tr(r)}); bu nedenle "
            f"eğilim testi yapılmadı." if tr_ else
            f" The values are not comparable across years ({r['not_comparable']}), so no trend "
            f"is tested.")
    if n >= r["min_points"]:
        return text + (" Değerler değişmediği için eğilim testi yapılmadı." if tr_
                       else " The values do not vary, so no trend is tested.")
    count = _count(n, lang).capitalize()
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


def _headline_tr(item: dict) -> str:
    figure = _amount(item["value"], item["unit"], "tr", exact=item["exact"])
    before = ", seçilen dönemden önce" if item["before"] else ""
    sector = item.get("sector_tr") or "sektör"
    caveats = []
    if item["not_comparable"]:
        caveats.append("önceki yıllar farklı bir temelde raporlandığı için karşılaştırılamaz")
    if item["caveat"] == "not_overall":
        caveats.append(f"bu rakam planın genel “{sector}” rakamı değil")
    elif item["caveat"] == "maybe_not_overall":
        caveats.append(f"bu rakam planın genel “{sector}” rakamı olmayabilir")
    return (f"{item['name']}: {figure} ({_when(item['period'], item['resolution'], 'tr')}{before})"
            + (f"; {'; '.join(caveats)}" if caveats else "") + ".")


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


def summary_facts(findings, language: str) -> str:
    """The Executive Summary's computed paragraph: the period, a sector's own figures,
    what the tests found, the look-back and the main limitation."""
    lang = _lang(language)
    tr_ = lang == "tr"
    out = []
    if findings.date_from:
        span = (f"{_day(findings.date_from, lang)} – {_day(findings.date_to, lang)}" if tr_
                else f"{_day(findings.date_from, lang)} to {_day(findings.date_to, lang)}")
        if findings.default_years:
            years = _count(findings.default_years, lang)
            span += (f" (dönem seçilmedi: son {years} yıl)" if tr_
                     else f" (no period was chosen: the last {years} years)")
        out.append(f"{'Analiz edilen dönem' if tr_ else 'Period analysed'}: {span}.")
    if tr_:
        out += [_headline_tr(item) for item in findings.headline_items]
    else:
        out += list(findings.headline)
    latest = _latest_values(findings, lang)
    if latest:
        out.append(f"{'Son değerler' if tr_ else 'Latest values'}: {'; '.join(latest)}.")
    tested = _tested(findings)
    holm = len(tested) >= 2
    significant = [s.heading for s in tested if s.stat_result["significant"]]
    if not tested:
        out.append("İstatistiksel test yapılamadı; bulgular gözlenen değerleriyle raporlanıyor." if tr_
                   else "No statistical test was possible; the findings are reported as their "
                        "observed values.")
    elif len(tested) == 1:
        heading = tested[0].heading
        if tr_:
            out.append(f"Bu raporda bir istatistiksel test yapıldı ({heading}); sonuç 0,05 "
                       f"düzeyinde istatistiksel olarak anlamlı{'' if significant else ' değil'}.")
        else:
            out.append(f"This report ran one statistical test ({heading}); its result is "
                       f"{'' if significant else 'not '}statistically significant at the 0.05 level.")
    else:
        n = _count(len(tested), lang)
        if tr_:
            after = " Holm düzeltmesinden sonra" if holm else ""
            out.append(
                f"Bu raporda {n} istatistiksel test yapıldı; 0,05 düzeyinde{after} "
                + (f"istatistiksel olarak anlamlı olanlar: {'; '.join(significant)}." if significant
                   else "hiçbiri istatistiksel olarak anlamlı değil."))
        else:
            after = " after the Holm correction" if holm else ""
            out.append(
                f"This report ran {n} statistical tests; "
                + (f"statistically significant at the 0.05 level{after}: {'; '.join(significant)}."
                   if significant else f"{'neither' if len(tested) == 2 else 'none'} is statistically "
                                           f"significant at the 0.05 level{after}."))
    looked = [s.stat_result for s in findings.sections if s.stat_result.get("look_back")]
    if looked:
        names = ", ".join(dict.fromkeys(r["indicator"] for r in looked))
        lb = looked[0]["look_back"]
        if tr_:
            out.append(f"Seçilen dönemdeki gözlem sayısı şu göstergeler için yetersiz: {names}. "
                       f"Bu göstergelerin değerleri ve eğilimleri daha uzun geriye bakış "
                       f"penceresini kapsıyor ({_day(lb['date_from'], lang)} – "
                       f"{_day(lb['date_to'], lang)}).")
        else:
            out.append(f"The chosen period holds too few observations for {names}, so their "
                       f"values and trends cover the longer look-back window "
                       f"{_day(lb['date_from'], lang)} to {_day(lb['date_to'], lang)}.")
    out.append(_limitation(findings, lang, short=True))
    return " ".join(out)


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
        return (f"{series}dır; testler gözlemlerin bağımsız olduğunu varsayar ve ardışık "
                "dönemler arasındaki seri korelasyon düzeltilmez, bu nedenle sonuçlar gösterge "
                "niteliğindedir.")
    series = "Most of the series are short" if some_long else "The series are short"
    if not tested:
        return f"{series}, so the values are descriptive."
    if short:
        return f"{series}, so the results are indicative."
    return (f"{series}; the tests assume independent observations and serial "
            "correlation between consecutive periods is not corrected for, so the results are "
            "indicative.")


_GAPS_TR = {
    "not_retrieved": "HDX HAPI'den alınamadı",
    "no_data": "dönemde veri yok",
    "too_few": "eğilim testi için gözlem sayısı yetersiz (n={n})",
    "not_comparable": "yıllar karşılaştırılabilir olmadığından eğilim testi yapılmadı",
    "analysis_error": "analiz hatası",
}
_GAPS_EN = {
    "not_retrieved": "could not be retrieved from HDX HAPI",
    "no_data": "no data in the period",
    "too_few": "too few observations for a trend test (n={n})",
    "not_comparable": "years not comparable, so no trend was tested",
    "analysis_error": "analysis error",
}
_WINDOW_TR = {"chosen": " (seçilen dönem)", "look_back": " (geriye bakış penceresi)", None: ""}


def _note_tr(item: dict) -> str:
    kind, name = item["kind"], item["name"]
    if kind == "plan_line":
        sector = item["sector_tr"]
        listed = ", ".join(f"{n} {_loc(tr._full(v), 'tr')}" for n, v in item["lines"])
        figure = _loc(tr._full(item["figure"]), "tr")
        what = (f"bu rakam ({figure}) bu satırlardan birinin altında olduğundan planın genel "
                f"“{sector}” rakamı değil; HDX HAPI bunun planın hangi satırı olduğunu belirtmiyor"
                if item["below"] else
                f"bu rakam ({figure}), planın genel “{sector}” rakamı yerine (HDX HAPI'de "
                f"listelenmeyen) başka bir “{sector}” satırı olabilir")
        return (f"{name}, {item['year']}: plan “{sector}” başlığını ayrı satırlarda raporluyor "
                f"({listed}); {what}; kişiler birden fazla satırda sayılabildiği için bu raporda "
                f"satırlar toplanmadı.")
    prefix = f"{name}{_WINDOW_TR[item.get('window')]}: "
    if kind == "dtm":
        parts = [f"yalnızca “{item['operation']}” adlı DTM operasyonu kullanıldı"]
        if item["other_operations"]:
            parts.append(f"yerinden edilmeyi farklı sayan {item['other_operations']} başka "
                         f"operasyon karıştırılmadı")
        if item["incomplete_rounds"]:
            parts.append(f"bölgelerinin %80'inden azını kapsayan {item['incomplete_rounds']} "
                         f"eksik tur dışarıda bırakıldı")
        return prefix + "; ".join(parts)
    if kind == "ipc":
        low, high = (_loc(f"{v / 1e6:.1f}", "tr") for v in (item["low"], item["high"]))
        return (f"{prefix}IPC analizleri farklı dönemlerde ülkenin farklı bölümlerini kapsadı "
                f"(analiz edilen nüfus {low} – {high} milyon); bu nedenle kişi sayısı değil, "
                f"analiz edilen nüfus içindeki pay kullanıldı")
    years = []
    for t in item["years"]:
        blank = f"kırılımsız {_loc(tr._full(t['blank']), 'tr')}" + (
            " (kullanılan)" if t["used"] == "" else "")
        total = f"kırılım toplamı {_loc(tr._full(t['total']), 'tr')}" + (
            " (kullanılan)" if t["used"] == "total" else "")
        years.append(f"{t['year']}: {blank} ve {total}")
    return (f"{prefix}HDX HAPI iki toplam içeriyor ({'; '.join(years)}); HNO'nun yayımladığı "
            f"sektör rakamı farklı olabilir")


def coverage_text(findings, language: str) -> str:
    """Data Coverage & Limitations: the gaps, what each series leaves out, the limitation."""
    lang = _lang(language)
    # A series whose years are not comparable gives that as its reason here too, not
    # "too few observations" (its finding says "not comparable … so no trend is tested").
    not_comparable = {s.stat_result["indicator"] for s in findings.sections
                      if s.stat_result.get("not_comparable")}
    wording = _GAPS_TR if lang == "tr" else _GAPS_EN
    gaps = [f"{g['name']}: " + wording["not_comparable" if g["name"] in not_comparable
                                       else g["code"]].format(n=g.get("n"))
            for g in findings.gap_items] or list(findings.gaps)
    if lang == "tr":
        notes = [_note_tr(n) for n in findings.note_items]
        labels = ("Veri boşlukları:", "Veri notları:", "Sınırlılık:")
    else:
        notes = list(findings.notes)
        labels = ("Data gaps:", "Data notes:", "Limitation:")
    out = []
    for label, items in zip(labels, (gaps, notes)):
        if items:
            out.append(label + "\n\n" + "\n".join(f"- {i.rstrip('.')}" for i in items))
    limitation = _limitation(findings, lang)
    out.append(f"{labels[2]} {limitation[0].lower()}{limitation[1:]}")
    return "\n\n".join(out)


def methods_text(findings, language: str, comparison_heading: str | None = None) -> str:
    """The methods this report used (and only those), and who wrote what.
    *comparison_heading*: the model-written section's heading, when the report has one."""
    lang = _lang(language)
    tr_ = lang == "tr"
    kinds = [s.stat_result["kind"] for s in _tested(findings)]
    out = []
    if not kinds:
        out.append("İstatistiksel test yapılamadı: her bulgu gözlenen değerleriyle raporlandı." if tr_
                   else "No statistical test was possible: every finding is reported as its "
                        "observed values.")
    if "trend" in kinds:
        out.append("Eğilim: Mann-Kendall testi; eğim, dönemlerin gerçek tarihleri üzerinden yıl "
                   "başına Sen eğimidir; etki büyüklüğü Kendall tau'dur." if tr_ else
                   "Trend: Mann-Kendall test; the slope is Sen's slope per year on the real dates "
                   "of the periods; Kendall's tau is the effect size.")
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
                   f"uygulandı; anlamlılık 0,05 düzeyinde Holm düzeltmeli p-değerine göre "
                   f"belirlendi." if tr_ else
                   f"Multiple comparisons: Holm correction across "
                   f"{'both' if len(kinds) == 2 else f'all {n}'} tests in this report; "
                   f"significance is decided on the Holm-adjusted p-value at the 0.05 level.")
    elif kinds:
        out.append("Tek bir istatistiksel test yapıldığı için çoklu karşılaştırma düzeltmesi "
                   "uygulanmadı; anlamlılık 0,05 düzeyinde testin p-değerine göre belirlendi."
                   if tr_ else
                   "One statistical test was run, so no multiple-comparison correction applies; "
                   "significance is decided on its p-value at the 0.05 level.")
    if tr_:
        out.append("Veriler HDX HAPI'den (Humanitarian Data Exchange'in veri API'si) alındı; "
                   "kullanılan veri setleri kaynak listesindedir. Bu rapordaki değerler, testler "
                   "ve sonuçlar kodla hesaplandı ve metin koddan üretildi"
                   + (f"; yalnızca “{comparison_heading}” bölümünü, bu rapor ile önceki raporu "
                      f"karşılaştıran bir yapay zekâ modeli yazdı." if comparison_heading
                      else "; hiçbir bölümü yapay zekâ modeli yazmadı."))
    else:
        out.append("The data come from HDX HAPI (the Humanitarian Data Exchange's data API); the "
                   "datasets used are in the source list. The values, tests and verdicts in this "
                   "report are computed in code, and its text is generated from them in code"
                   + (f"; only the section “{comparison_heading}” is written by an AI model, "
                      f"comparing this report with the previous one." if comparison_heading
                      else "; no part of it is written by an AI model."))
    return " ".join(out)


def opening(findings, language: str) -> str:
    """The report's first block, shown before the model has written a word."""
    return f"## {HEADINGS[_lang(language)]['summary']}\n\n{summary_facts(findings, language)}"


def section_block(section, language: str) -> str:
    return f"## {section.heading}\n\n{section_facts(section.stat_result, language)}"


def closing(findings, language: str, comparison_heading: str | None = None) -> str:
    """Data Coverage & Limitations and Methods."""
    h = HEADINGS[_lang(language)]
    return (f"## {h['coverage']}\n\n{coverage_text(findings, language)}\n\n"
            f"## {h['methods']}\n\n{methods_text(findings, language, comparison_heading)}")


def assemble(findings, language: str, comparison: tuple[str, str] | None = None) -> str:
    """The whole report. *comparison*: (heading, text) of a next-period report's "What
    changed" section, placed right after the Executive Summary."""
    has_comparison = bool(comparison and comparison[1] and comparison[1].strip())
    parts = [opening(findings, language)]
    if has_comparison:
        parts.append(f"## {comparison[0]}\n\n{comparison[1].strip()}")
    parts += [section_block(s, language) for s in findings.sections]
    parts.append(closing(findings, language, comparison[0] if has_comparison else None))
    return "\n\n".join(parts)
