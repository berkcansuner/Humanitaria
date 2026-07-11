from config import Settings


def test_hapi_settings_have_defaults():
    s = Settings()
    assert s.HDX_HAPI_BASE_URL == "https://hapi.humdata.org/api/v1"
    assert s.HDX_HAPI_TIMEOUT == 30
    assert s.HDX_HAPI_ADMIN_LEVEL == 1
    assert s.TECHNICAL_REPORT_MIN_POINTS == 4
    assert s.HDX_APP_IDENTIFIER == ""


def test_analytics_deps_importable():
    import pandas  # noqa: F401
    import scipy  # noqa: F401
    import pymannkendall  # noqa: F401
    import matplotlib  # noqa: F401
