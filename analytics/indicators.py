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

    def name(self, language: str = "tr") -> str:
        """The indicator's name in the report language (Turkish unless "en")."""
        return self.label_en if language == "en" and self.label_en else self.label


INDICATORS: list[Indicator] = [
    Indicator("humanitarian_needs", "İnsani ihtiyaç (kişi)",
              "affected-people/humanitarian-needs", "population", "sum", 0,
              {"population_status": "INN", "sector_code": "Intersectoral"},
              label_en="People in need (people)", source="OCHA HNO"),
    # Share of the analysed population in IPC 3+, not people: an IPC analysis may cover
    # only part of a country (Yemen alternates ~35M nationwide / ~10M government-held
    # areas), so counts from different periods are not comparable; the share is.
    Indicator("food_security", "Gıda güvensizliği (IPC 3+, analiz edilen nüfusun %'si)",
              "food/food-security", "population_fraction_in_phase", "mean", 0,
              {"ipc_type": "current", "ipc_phase": "3+"}, scale=100, unit="percentage points",
              label_en="Food insecurity (IPC 3+, % of the analysed population)", source="IPC"),
    Indicator("refugees", "Mülteci (kişi)",
              "affected-people/refugees", "population", "sum", 0,
              {"gender": "all", "age_range": "all", "population_group": "REF"},
              location_param="origin_location_code",
              label_en="Refugees (people)", source="UNHCR"),
    Indicator("returnees", "Dönüş yapan (kişi)",
              "affected-people/returnees", "population", "sum", 0,
              {"gender": "all", "age_range": "all", "population_group": "RET"},
              location_param="origin_location_code",
              label_en="Returnees (people)", source="UNHCR"),
    Indicator("idps", "Yerinden edilmiş kişi (IDP)",
              "affected-people/idps", "population", "sum", 1,
              {"gender": "all", "age_range": "all"},
              label_en="Internally displaced people (IDPs)", source="IOM DTM",
              # IOM's terms (https://dtm.iom.int/terms-and-conditions) require this credit
              # line and the source URL wherever DTM data is shown.
              credit="International Organization for Migration (IOM), {month_year}, "
                     "Displacement Tracking Matrix (DTM), https://dtm.iom.int"),
    Indicator("funding", "İnsani fonlama (USD)",
              "coordination-context/funding", "funding_usd", "sum", 0, {},
              complete_periods_only=True,
              label_en="Humanitarian funding (USD)", source="OCHA FTS"),
]

_BY_KEY = {i.key: i for i in INDICATORS}


def by_key(key: str) -> Indicator | None:
    return _BY_KEY.get(key)
