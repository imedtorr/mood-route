import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

GEOCODE_CACHE: dict[str, tuple[float, float, str, str]] = {}

NOMINATIM_HEADERS = {"User-Agent": "MoodRoute/1.0 (travel-app)"}

FOOD_CATEGORIES = frozenset({"Restaurant", "Cafe", "Market"})

COUNTRY_CODES: dict[str, str] = {
    "china": "cn",
    "japan": "jp",
    "south korea": "kr",
    "korea": "kr",
    "taiwan": "tw",
    "thailand": "th",
    "vietnam": "vn",
    "singapore": "sg",
    "india": "in",
    "united states": "us",
    "usa": "us",
    "united kingdom": "gb",
    "uk": "gb",
    "france": "fr",
    "germany": "de",
    "italy": "it",
    "spain": "es",
    "russia": "ru",
}

ADDRESS_PATTERNS = (
    re.compile(
        r"No\.?\s*\d+[^,.;\n]+(?:Road|Street|Avenue|Blvd\.?|Lane|Rd\.?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\d+\s+[\w\s']+(?:Road|Street|Avenue|Rue|straße|Rd\.?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"[\w\s']+(?:Road|Street|Avenue),?\s*\w+\s+District",
        re.IGNORECASE,
    ),
)

DISTRICT_PATTERN = re.compile(r"([\w\s']+?\s+District)", re.IGNORECASE)
STREET_PATTERN = re.compile(
    r"^([\w\s']+(?:Road|Street|Avenue|Blvd\.?|Lane|Rd\.?))",
    re.IGNORECASE,
)
COORD_PATTERN = re.compile(r"(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})")


def _country_code(country: str) -> str:
    return COUNTRY_CODES.get((country or "").strip().lower(), "")


def _normalize_address(text: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", "", text or "")
    cleaned = cleaned.replace("'", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    return cleaned


def _extract_district(text: str) -> str:
    match = DISTRICT_PATTERN.search(text or "")
    return _normalize_address(match.group(1)) if match else ""


def _extract_street(text: str) -> str:
    normalized = _normalize_address(text)
    match = STREET_PATTERN.match(normalized)
    return match.group(1).strip() if match else ""


def _parse_coordinate_pair(a: float, b: float, country: str) -> tuple[float, float] | None:
    country_lower = (country or "").lower()
    if country_lower == "china":
        if 18 <= a <= 54 and 73 <= b <= 135:
            return a, b
        if 18 <= b <= 54 and 73 <= a <= 135:
            return b, a
        return None
    if -90 <= a <= 90 and -180 <= b <= 180:
        return a, b
    if -90 <= b <= 90 and -180 <= a <= 180:
        return b, a
    return None


def _extract_coordinates(text: str, country: str) -> list[tuple[float, float]]:
    found: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for match in COORD_PATTERN.finditer(text or ""):
        pair = _parse_coordinate_pair(float(match.group(1)), float(match.group(2)), country)
        if pair and pair not in seen:
            seen.add(pair)
            found.append(pair)
    return found


def _location_tokens(*parts: str) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        for token in re.split(r"[\s,]+", (part or "").lower()):
            token = token.strip("'")
            if len(token) >= 3:
                tokens.add(token)
    return tokens


def _photon_matches_location(properties: dict, city: str, district: str) -> bool:
    if not city and not district:
        return True
    expected = _location_tokens(city, district)
    if not expected:
        return True
    actual = _location_tokens(
        properties.get("city", ""),
        properties.get("district", ""),
        properties.get("county", ""),
        properties.get("state", ""),
        properties.get("name", ""),
    )
    return bool(expected & actual)


async def _nominatim_search(
    query: str,
    *,
    country: str = "",
    street: str = "",
    city: str = "",
) -> tuple[float | None, float | None, str, str]:
    country_code = _country_code(country)

    async def _request(params: dict) -> tuple[float | None, float | None, str, str]:
        try:
            if country_code:
                params = {**params, "countrycodes": country_code}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={**params, "format": "json", "limit": 1},
                    headers=NOMINATIM_HEADERS,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    return None, None, "", ""
                item = data[0]
                lat = float(item["lat"])
                lng = float(item["lon"])
                display_name = item.get("display_name", "")
                district_name = display_name.split(",")[0] if display_name else ""
                return lat, lng, district_name, display_name
        except Exception:
            logger.debug("Nominatim search failed for params: %s", params, exc_info=True)
            return None, None, "", ""

    if street and city and country:
        structured = await _request({"street": street, "city": city, "country": country})
        if structured[0] is not None:
            return structured

    return await _request({"q": query})


async def _photon_search(
    query: str,
    *,
    city: str = "",
    district: str = "",
) -> tuple[float | None, float | None, str, str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://photon.komoot.io/api/",
                params={"q": query, "limit": 5},
            )
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            for feature in features:
                properties = feature.get("properties", {})
                if not _photon_matches_location(properties, city, district):
                    continue
                coordinates = feature.get("geometry", {}).get("coordinates", [])
                if len(coordinates) < 2:
                    continue
                lng, lat = float(coordinates[0]), float(coordinates[1])
                district_name = (
                    properties.get("district")
                    or properties.get("city")
                    or properties.get("name")
                    or ""
                )
                resolved_address = ", ".join(
                    part
                    for part in [
                        properties.get("name"),
                        properties.get("street"),
                        properties.get("district"),
                        properties.get("city"),
                        properties.get("country"),
                    ]
                    if part
                )
                return lat, lng, district_name, resolved_address
    except Exception:
        logger.debug("Photon search failed for query: %s", query, exc_info=True)
    return None, None, "", ""


def _build_direct_queries(
    name: str,
    city: str,
    country: str,
    address: str,
    category: str,
) -> list[str]:
    queries: list[str] = []
    address = _normalize_address(address)
    title_hint = _normalize_address(_extract_title_location_hint(name))
    cleaned_name = _clean_search_title(name)
    district = _extract_district(address) or _extract_district(title_hint)

    if address:
        queries.append(", ".join(part for part in [address, city, country] if part))
    if title_hint:
        queries.append(", ".join(part for part in [title_hint, city, country] if part))
        if cleaned_name:
            queries.append(
                ", ".join(part for part in [cleaned_name, title_hint, city, country] if part)
            )
    if district:
        queries.append(", ".join(part for part in [district, city, country] if part))
    if name and city and country:
        queries.append(f"{name}, {city}, {country}")
        if category in FOOD_CATEGORIES:
            queries.append(f"{name} restaurant, {city}, {country}")
            queries.append(f"{category} {name}, {city}, {country}")
    if name and city:
        queries.append(f"{name} {city}")
    if city and country:
        queries.append(f"{city}, {country}")
    return queries


def _extract_addresses(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern in ADDRESS_PATTERNS:
        for match in pattern.finditer(text):
            candidate = _normalize_address(match.group(0))
            key = candidate.lower()
            if candidate and key not in seen:
                seen.add(key)
                found.append(candidate)
    return found


def _clean_search_title(title: str) -> str:
    cleaned = re.split(r"\s[-|–—]\s", title, maxsplit=1)[0].strip()
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned).strip()
    return cleaned


def _extract_title_location_hint(title: str) -> str:
    match = re.search(r"\(([^)]+)\)", title or "")
    return match.group(1).strip() if match else ""


def _discover_via_web(
    name: str,
    city: str,
    country: str,
    category: str,
) -> tuple[list[str], list[tuple[float, float, str, str]]]:
    from app.services.tavily import tavily_service

    if not tavily_service.available:
        return [], []

    kind = category.lower() if category in FOOD_CATEGORIES else "place"
    extra = " coordinates map 地址" if _country_code(country) == "cn" else " coordinates map"
    query = f"{name} {city} {country} {kind} address location{extra}"
    results = tavily_service.search(query, max_results=3)
    discovered: list[str] = []
    coordinates: list[tuple[float, float, str, str]] = []
    seen_queries: set[str] = set()
    seen_coords: set[tuple[float, float]] = set()

    def add(candidate: str) -> None:
        candidate = _normalize_address(candidate)
        if not candidate:
            return
        key = candidate.lower()
        if key in seen_queries:
            return
        seen_queries.add(key)
        discovered.append(candidate)

    for result in results:
        title = _clean_search_title(result.get("title", ""))
        content = result.get("content", "")
        if title:
            add(f"{title}, {city}, {country}")
        for fragment in _extract_addresses(content):
            add(f"{fragment}, {city}, {country}")
            add(f"{fragment}, {city}")
        for lat, lng in _extract_coordinates(content, country):
            if (lat, lng) in seen_coords:
                continue
            seen_coords.add((lat, lng))
            coordinates.append((lat, lng, city, f"{name}, {city}"))

    return discovered, coordinates


async def _run_queries(
    queries: list[str],
    city: str,
    country: str = "",
    district: str = "",
    *,
    start_index: int = 0,
) -> tuple[float | None, float | None, str, str]:
    seen_queries: set[str] = set()

    for index, query in enumerate(queries):
        normalized = query.lower()
        if not query or normalized in seen_queries:
            continue
        seen_queries.add(normalized)

        if normalized in GEOCODE_CACHE:
            return GEOCODE_CACHE[normalized]

        if index > start_index:
            await asyncio.sleep(1.1)

        lat, lng, found_district, resolved_address = await _nominatim_search(
            query,
            country=country,
            street=_extract_street(query),
            city=city,
        )
        if lat is None or lng is None:
            lat, lng, found_district, resolved_address = await _photon_search(
                query,
                city=city,
                district=district,
            )

        if lat is not None and lng is not None:
            fallback_district = found_district or district or city
            result = (lat, lng, fallback_district, resolved_address)
            GEOCODE_CACHE[normalized] = result
            return result

    return None, None, city, ""


async def geocode_place(
    name: str,
    city: str,
    country: str = "Japan",
    address: str = "",
    category: str = "",
) -> tuple[float | None, float | None, str, str]:
    """Return (lat, lng, district, resolved_address)."""
    address = _normalize_address((address or "").strip())
    name = (name or "").strip()
    city = (city or "").strip()
    country = (country or "").strip()
    category = (category or "").strip()
    title_hint = _normalize_address(_extract_title_location_hint(name))
    district = _extract_district(address) or _extract_district(title_hint)

    direct_queries = _build_direct_queries(_clean_search_title(name), city, country, address, category)
    result = await _run_queries(direct_queries, city, country, district)
    if result[0] is not None:
        return result

    web_queries, web_coordinates = _discover_via_web(name, city, country, category)
    for lat, lng, coord_district, resolved_address in web_coordinates:
        return lat, lng, coord_district, resolved_address

    if web_queries:
        return await _run_queries(
            web_queries,
            city,
            country,
            district,
            start_index=len(direct_queries),
        )

    return None, None, city, ""
