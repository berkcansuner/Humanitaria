"""M&E-ilgili HDX HAPI indikatörleri → endpoint + admin_level + değer alanı +
sunucu-tarafı query_params.

`query_params`: HAPI'ye sunucu-tarafı gönderilen boyut filtreleri; demografik
fan-out'u kaynağında keser ve agregat (doğru toplam) satırları getirir. `admin_level`:
bu indikatörün çekileceği idari düzey. `aggregation`: aynı dönem için birden çok
satır (sığınma ülkeleri / ilçeler) nasıl birleştirilir (sum = topla).
`location_param`: HAPI'ye ülke filtresi hangi query param ile gönderilir; sınır-ötesi
endpoint'ler (refugees/returnees) `location_code`'u yok sayıp global veri döndürür —
bunlar `origin_location_code` (menşe ülke) kullanır. Diğerleri varsayılan `location_code`.
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Indicator:
    key: str
    label: str
    endpoint: str            # "theme/subcategory"
    value_field: str         # HAPI satırındaki sayısal alan
    aggregation: str         # sum | mean | latest
    admin_level: int         # 0 = ulusal agregat, 1/2 = alt-ulusal
    query_params: dict = field(default_factory=dict)
    location_param: str = "location_code"
    # A flow that accumulates over its period (funding): an unfinished period's
    # partial total would read as a fall, so only completed periods are used.
    complete_periods_only: bool = False
    scale: float = 1.0       # value_field × scale (a 0-1 share → percent)
    unit: str = ""           # unit of the trend slope ("" = the indicator's own count)
    label_en: str = ""       # English name; `label` is the Turkish one
    source: str = ""         # who publishes the data HDX HAPI serves (printed under charts)
    # The publisher's required credit line, when it has one; {month_year} is the month of
    # the latest data shown. Printed instead of `source`.
    credit: str = ""
    # A sector's people in need: its name when HAPI's figure is the plan's general line
    # (the plan reports sub-lines such as child protection separately), and the sector
    # in plain English for the findings' notes.
    general_label: str = ""
    general_label_en: str = ""
    sector_en: str = ""

    def name(self, language: str = "tr") -> str:
        """The indicator's name in the report language: Turkish for "tr", else English
        (as the section headings are)."""
        return self.label if language == "tr" or not self.label_en else self.label_en

    def general_name(self, language: str = "tr") -> str:
        """The name of the sector's general line, in the report language."""
        if not self.general_label:
            return self.name(language)
        return self.general_label if language == "tr" else self.general_label_en


INDICATORS: list[Indicator] = [
    Indicator("humanitarian_needs", "İnsani yardıma ihtiyaç duyan kişiler",
              "affected-people/humanitarian-needs", "population", "sum", 0,
              {"population_status": "INN", "sector_code": "Intersectoral"},
              label_en="People in need (people)", source="OCHA HNO"),
    # Share of the analysed population in IPC 3+, not people: an IPC analysis may cover
    # only part of a country (Yemen alternates ~35M nationwide / ~10M government-held
    # areas), so counts from different periods are not comparable; the share is.
    Indicator("food_security", "Gıda güvensizliği (IPC 3+, analiz edilen nüfusun yüzdesi)",
              "food/food-security", "population_fraction_in_phase", "mean", 0,
              {"ipc_type": "current", "ipc_phase": "3+"}, scale=100, unit="percentage points",
              label_en="Food insecurity (IPC 3+, % of the analysed population)", source="IPC"),
    Indicator("refugees", "Mülteciler (kişi)",
              "affected-people/refugees", "population", "sum", 0,
              {"gender": "all", "age_range": "all", "population_group": "REF"},
              location_param="origin_location_code",
              label_en="Refugees (people)", source="UNHCR"),
    Indicator("returnees", "Geri dönenler (kişi)",
              "affected-people/returnees", "population", "sum", 0,
              {"gender": "all", "age_range": "all", "population_group": "RET"},
              location_param="origin_location_code",
              label_en="Returnees (people)", source="UNHCR"),
    Indicator("idps", "Ülke içinde yerinden edilmiş kişiler (IDP)",
              "affected-people/idps", "population", "sum", 1,
              {"gender": "all", "age_range": "all"},
              label_en="Internally displaced people (IDPs)", source="IOM DTM",
              # IOM's terms (https://dtm.iom.int/terms-and-conditions) require this credit
              # line and the source URL wherever DTM data is shown.
              credit="International Organization for Migration (IOM), {month_year}, "
                     "Displacement Tracking Matrix (DTM), https://dtm.iom.int"),
    Indicator("funding", "İnsani yardım fonlaması (USD)",
              "coordination-context/funding", "funding_usd", "sum", 0, {},
              complete_periods_only=True,
              label_en="Humanitarian funding (USD)", source="OCHA FTS"),
]



def _sector_pin(key: str, sector_code: str, label_tr: str, label_en: str) -> Indicator:
    """People in need of one HNO sector (cluster), as OCHA's HNO counts them."""
    return Indicator(key, f"{label_tr}: insani yardıma ihtiyaç duyan kişiler",
                     "affected-people/humanitarian-needs", "population", "sum", 0,
                     {"population_status": "INN", "sector_code": sector_code},
                     label_en=f"{label_en}: people in need", source="OCHA HNO",
                     general_label=f"Genel {label_tr[0].lower()}{label_tr[1:]}: insani yardıma "
                                   f"ihtiyaç duyan kişiler",
                     general_label_en=f"General {label_en[0].lower()}{label_en[1:]}: people in need",
                     sector_en=f"{label_en[0].lower()}{label_en[1:]}")


# HNO sector codes as HDX HAPI serves them (checked 2026-11-18 for AFG, SDN, SYR, YEM;
# one figure per HNO year, from 2024).
SECTOR_INDICATORS: list[Indicator] = [
    _sector_pin("pin_food_security", "FSC", "Gıda güvenliği", "Food security"),
    _sector_pin("pin_nutrition", "NUT", "Beslenme", "Nutrition"),
    _sector_pin("pin_health", "HEA", "Sağlık", "Health"),
    _sector_pin("pin_protection", "PRO", "Koruma", "Protection"),
    _sector_pin("pin_gbv", "PRO-GBV", "Toplumsal cinsiyete dayalı şiddet", "Gender-based violence"),
    _sector_pin("pin_mine_action", "PRO-MIN", "Mayın faaliyetleri", "Mine action"),
    _sector_pin("pin_wash", "WSH", "Su, sanitasyon ve hijyen", "Water, sanitation and hygiene"),
    _sector_pin("pin_education", "EDU", "Eğitim", "Education"),
    _sector_pin("pin_shelter", "SHL", "Acil barınma ve gıda dışı malzemeler",
                "Emergency shelter and non-food items"),
    _sector_pin("pin_cccm", "CCM", "Kamp koordinasyonu ve kamp yönetimi",
                "Camp coordination and camp management"),
    _sector_pin("pin_early_recovery", "ERY", "Erken toparlanma", "Early recovery"),
]

# The form's sectors (api.routes.reports.THEMES) → the HAPI series a technical report on
# that sector analyses, its own people-in-need figure first. A sector left out has no
# quantitative HAPI series, and gets no report made of other sectors' figures. Funding
# has no sector dimension in HAPI (FTS appeal totals), so it is only the financing
# themes' subject, never presented as one sector's funding.
THEME_INDICATORS: dict[str, tuple[str, ...]] = {
    "Camp Coordination and Camp Management": ("pin_cccm", "idps"),
    "Contributions": ("funding",),
    "Education": ("pin_education",),
    "Food and Nutrition": ("pin_food_security", "pin_nutrition", "food_security"),
    "Gender": ("pin_gbv",),
    "Health": ("pin_health",),
    "Humanitarian Financing": ("funding",),
    "Mine Action": ("pin_mine_action",),
    "Protection and Human Rights": ("pin_protection", "refugees", "returnees", "idps"),
    "Recovery and Reconstruction": ("pin_early_recovery",),
    "Shelter and Non-Food Items": ("pin_shelter",),
    "Water Sanitation Hygiene": ("pin_wash",),
}

_BY_KEY = {i.key: i for i in INDICATORS + SECTOR_INDICATORS}


def indicators_for(theme: str | None) -> list[Indicator]:
    """The indicators a technical report on *theme* analyses: all six overview
    indicators for "All sectors" (None), the sector's own series otherwise, and none
    for a sector HAPI has no series for."""
    if theme is None:
        return INDICATORS
    return [_BY_KEY[k] for k in THEME_INDICATORS.get(theme, ())]


def by_key(key: str) -> Indicator | None:
    return _BY_KEY.get(key)
