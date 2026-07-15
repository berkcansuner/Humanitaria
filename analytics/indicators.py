"""M&E-ilgili HDX HAPI indikatörleri → endpoint + admin_level + değer alanı +
sunucu-tarafı query_params.

`query_params`: HAPI'ye sunucu-tarafı gönderilen boyut filtreleri; demografik
fan-out'u kaynağında keser ve agregat (doğru toplam) satırları getirir. `admin_level`:
bu indikatörün çekileceği idari düzey (conflict yalnız admin2'de veri taşır).
`aggregation`: aynı dönem için birden çok satır (sığınma ülkeleri / ilçeler) nasıl
birleştirilir (sum = topla).
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


INDICATORS: list[Indicator] = [
    Indicator("humanitarian_needs", "İnsani ihtiyaç (kişi)",
              "affected-people/humanitarian-needs", "population", "sum", 0,
              {"population_status": "INN", "sector_code": "Intersectoral"}),
    Indicator("food_security", "Gıda güvensizliği (kişi)",
              "food/food-security", "population_in_phase", "sum", 0,
              {"ipc_type": "current", "ipc_phase": "3+"}),
    Indicator("conflict_events", "Çatışma kaynaklı ölüm",
              "coordination-context/conflict-event", "fatalities", "sum", 2, {}),
    Indicator("refugees", "Mülteci (kişi)",
              "affected-people/refugees", "population", "sum", 0,
              {"gender": "all", "age_range": "all", "population_group": "REF"}),
    Indicator("returnees", "Dönüş yapan (kişi)",
              "affected-people/returnees", "population", "sum", 0,
              {"gender": "all", "age_range": "all", "population_group": "RET"}),
    Indicator("idps", "Yerinden edilmiş kişi (IDP)",
              "affected-people/idps", "population", "sum", 1,
              {"gender": "all", "age_range": "all"}),
    Indicator("funding", "İnsani fonlama (USD)",
              "coordination-context/funding", "funding_usd", "sum", 0, {}),
]

_BY_KEY = {i.key: i for i in INDICATORS}


def by_key(key: str) -> Indicator | None:
    return _BY_KEY.get(key)
