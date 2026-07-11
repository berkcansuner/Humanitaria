"""M&E-ilgili HDX HAPI indikatörleri → endpoint + değer alanı + toplama kuralı.

`filters`: HAPI query'sine eklenen sabit filtreler; ulusal toplamda double-counting'i
önler (örn. humanitarian_needs'te yalnızca 'in need' (INN) satırları alınır, sektörler
üst üste toplanmaz). `aggregation`: aynı dönem-bölge için birden çok satır gelirse nasıl
birleştirileceği (sum = topla, mean = ortala, latest = en yeni).
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
    filters: dict = field(default_factory=dict)


INDICATORS: list[Indicator] = [
    Indicator("humanitarian_needs", "İnsani ihtiyaç (kişi)",
              "affected-people/humanitarian-needs", "population", "sum",
              {"population_status": "INN"}),
    Indicator("idps", "Yerinden edilmiş kişi (IDP)",
              "affected-people/idps", "population", "sum", {}),
    Indicator("refugees", "Mülteci (kişi)",
              "affected-people/refugees", "population", "sum", {}),
    Indicator("returnees", "Dönüş yapan (kişi)",
              "affected-people/returnees", "population", "sum", {}),
    Indicator("food_security", "Gıda güvensizliği (kişi)",
              "food-security-nutrition/food-security", "population", "sum", {}),
    Indicator("conflict_events", "Çatışma kaynaklı ölüm",
              "coordination-context/conflict-events", "fatalities", "sum", {}),
    Indicator("funding", "İnsani fonlama (USD)",
              "coordination-context/funding", "funding", "sum", {}),
]

_BY_KEY = {i.key: i for i in INDICATORS}


def by_key(key: str) -> Indicator | None:
    return _BY_KEY.get(key)
