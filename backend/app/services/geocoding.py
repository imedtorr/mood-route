import httpx

GEOCODE_CACHE: dict[str, tuple[float, float, str]] = {}


async def geocode_place(name: str, city: str, country: str = "Japan") -> tuple[float | None, float | None, str]:
    key = f"{name}|{city}|{country}".lower()
    if key in GEOCODE_CACHE:
        lat, lng, district = GEOCODE_CACHE[key]
        return lat, lng, district

    query = f"{name}, {city}, {country}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": "MoodRoute/1.0 (travel-app)"},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None, None, city
            item = data[0]
            lat = float(item["lat"])
            lng = float(item["lon"])
            district = item.get("display_name", city).split(",")[0]
            GEOCODE_CACHE[key] = (lat, lng, district)
            return lat, lng, district
    except Exception:
        return None, None, city
