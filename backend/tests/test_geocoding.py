import pytest

from app.services import geocoding


@pytest.fixture(autouse=True)
def clear_geocode_cache():
    geocoding.GEOCODE_CACHE.clear()
    yield
    geocoding.GEOCODE_CACHE.clear()


def test_normalize_address_strips_parentheses_and_apostrophes():
    raw = "Yitianmen Street, Nan'an District (near the Xixin Senior Apartment)"
    assert geocoding._normalize_address(raw) == "Yitianmen Street, Nanan District"


def test_extract_district_from_address():
    address = "Yitianmen Street, Nan'an District (near the Xixin Senior Apartment)"
    assert geocoding._extract_district(address) == "Nanan District"


def test_build_direct_queries_includes_title_hint_and_district_fallback():
    queries = geocoding._build_direct_queries(
        "Ding Lao Tou BBQ (Yitianmen Street, Nan'an District)",
        "Chongqing",
        "China",
        "Yitianmen Street, Nan'an District (near the Xixin Senior Apartment)",
        "Restaurant",
    )

    assert "Yitianmen Street, Nanan District, Chongqing, China" in queries
    assert "Nanan District, Chongqing, China" in queries
    assert any("Ding Lao Tou BBQ" in query for query in queries)


def test_extract_coordinates_for_china_swaps_lng_lat_when_needed():
    pairs = geocoding._extract_coordinates("located at 106.5932, 29.5584 in Chongqing", "China")
    assert pairs == [(29.5584, 106.5932)]


@pytest.mark.asyncio
async def test_geocode_place_uses_photon_when_nominatim_returns_empty(monkeypatch):
    async def fake_nominatim(*_args, **_kwargs):
        return None, None, "", ""

    async def fake_photon(query: str, *, city: str = "", district: str = ""):
        if "Yitianmen Street" in query:
            return (
                29.5584968,
                106.5932243,
                "南岸区",
                "一天门, 南岸区, Chongqing, China",
            )
        return None, None, "", ""

    monkeypatch.setattr(geocoding, "_nominatim_search", fake_nominatim)
    monkeypatch.setattr(geocoding, "_photon_search", fake_photon)
    monkeypatch.setattr(geocoding, "_discover_via_web", lambda *_args, **_kwargs: ([], []))

    lat, lng, district, resolved_address = await geocoding.geocode_place(
        "Ding Lao Tou BBQ (Yitianmen Street, Nan'an District)",
        "Chongqing",
        "China",
        "Yitianmen Street, Nan'an District (near the Xixin Senior Apartment)",
        "Restaurant",
    )

    assert lat == pytest.approx(29.5584968)
    assert lng == pytest.approx(106.5932243)
    assert district
    assert resolved_address


@pytest.mark.asyncio
async def test_geocode_place_uses_coordinates_from_tavily(monkeypatch):
    async def fake_nominatim(*_args, **_kwargs):
        return None, None, "", ""

    async def fake_photon(*_args, **_kwargs):
        return None, None, "", ""

    def fake_discover(*_args, **_kwargs):
        return (
            [],
            [(29.5012, 106.6418, "Chongqing", "Ding Lao Tou BBQ, Chongqing")],
        )

    monkeypatch.setattr(geocoding, "_nominatim_search", fake_nominatim)
    monkeypatch.setattr(geocoding, "_photon_search", fake_photon)
    monkeypatch.setattr(geocoding, "_discover_via_web", fake_discover)

    lat, lng, district, resolved_address = await geocoding.geocode_place(
        "Ding Lao Tou BBQ",
        "Chongqing",
        "China",
        "",
        "Restaurant",
    )

    assert lat == pytest.approx(29.5012)
    assert lng == pytest.approx(106.6418)
    assert district == "Chongqing"
    assert resolved_address
