import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

GEOCODE_CACHE: dict[str, tuple[float, float, str, str]] = {}

NOMINATIM_HEADERS = {"User-Agent": "MoodRoute/1.0 (travel-app)"}

FOOD_CATEGORIES = frozenset({"Restaurant", "Cafe", "Market"})

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


async def _nominatim_search(query: str) -> tuple[float | None, float | None, str, str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
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
            district = display_name.split(",")[0] if display_name else ""
            return lat, lng, district, display_name
    except Exception:
        logger.debug("Nominatim search failed for query: %s", query, exc_info=True)
        return None, None, "", ""


def _build_direct_queries(
    name: str,
    city: str,
    country: str,
    address: str,
    category: str,
) -> list[str]:
    queries: list[str] = []
    if address:
        queries.append(", ".join(part for part in [address, city, country] if part))
    if name and city and country:
        queries.append(f"{name}, {city}, {country}")
        if category in FOOD_CATEGORIES:
            queries.append(f"{name} restaurant, {city}, {country}")
            queries.append(f"{category} {name}, {city}, {country}")
    if name and city:
        queries.append(f"{name} {city}")
    return queries


def _extract_addresses(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern in ADDRESS_PATTERNS:
        for match in pattern.finditer(text):
            candidate = re.sub(r"\s+", " ", match.group(0)).strip(" ,.;")
            key = candidate.lower()
            if candidate and key not in seen:
                seen.add(key)
                found.append(candidate)
    return found


def _clean_search_title(title: str) -> str:
    cleaned = re.split(r"\s[-|–—]\s", title, maxsplit=1)[0].strip()
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    return cleaned


def _discover_queries_via_web(
    name: str,
    city: str,
    country: str,
    category: str,
) -> list[str]:
    from app.services.tavily import tavily_service

    if not tavily_service.available:
        return []

    kind = category.lower() if category in FOOD_CATEGORIES else "place"
    query = f"{name} {city} {country} {kind} address location"
    results = tavily_service.search(query, max_results=3)
    discovered: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        candidate = candidate.strip(" ,.;")
        if not candidate:
            return
        key = candidate.lower()
        if key in seen:
            return
        seen.add(key)
        discovered.append(candidate)

    for result in results:
        title = _clean_search_title(result.get("title", ""))
        content = result.get("content", "")
        if title:
            add(f"{title}, {city}, {country}")
        for fragment in _extract_addresses(content):
            add(f"{fragment}, {city}, {country}")
            add(f"{fragment}, {city}")

    return discovered


async def _run_queries(
    queries: list[str],
    city: str,
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

        lat, lng, district, resolved_address = await _nominatim_search(query)
        if lat is not None and lng is not None:
            fallback_district = district or city
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
    address = (address or "").strip()
    name = (name or "").strip()
    city = (city or "").strip()
    country = (country or "").strip()
    category = (category or "").strip()

    direct_queries = _build_direct_queries(name, city, country, address, category)
    result = await _run_queries(direct_queries, city)
    if result[0] is not None:
        return result

    web_queries = _discover_queries_via_web(name, city, country, category)
    if web_queries:
        return await _run_queries(web_queries, city, start_index=len(direct_queries))

    return None, None, city, ""
