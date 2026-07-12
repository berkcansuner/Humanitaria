"""Form ülke adı → ISO3 (HDX HAPI location_code). Form listesi sınırlı olduğundan
küçük, elle bakımlı bir harita yeterli; eşleşmeyen ülke net hata ile reddedilir."""

_ISO3 = {
    "Afghanistan": "AFG", "Bangladesh": "BGD", "Burkina Faso": "BFA",
    "Cameroon": "CMR", "Central African Republic": "CAF", "Chad": "TCD",
    "Colombia": "COL", "Democratic Republic of the Congo": "COD",
    "Ethiopia": "ETH", "Haiti": "HTI", "Iran": "IRN", "Iraq": "IRQ",
    "Lebanon": "LBN", "Mali": "MLI", "Mozambique": "MOZ", "Myanmar": "MMR",
    "Niger": "NER", "Nigeria": "NGA", "Pakistan": "PAK",
    "occupied Palestinian territory": "PSE", "Somalia": "SOM",
    "South Sudan": "SSD", "Sudan": "SDN", "Syrian Arab Republic": "SYR",
    "Ukraine": "UKR", "Venezuela": "VEN", "Yemen": "YEM",
}


def iso3_for(country: str) -> str | None:
    return _ISO3.get((country or "").strip())
