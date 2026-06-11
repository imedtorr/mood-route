"""Place normalization helpers.

Cyrillic entries in CITY_ALIASES and COUNTRY_ALIASES map common non-English
spellings from user input and OCR to canonical English names for storage and UI.
"""

import re

GENERIC_TITLES = {
    "discovered place",
    "travel inspirations",
    "travel place information",
    "unknown",
}

CITY_ALIASES = {
    "шанхай": "Shanghai",
    "shanghai": "Shanghai",
    "пекин": "Beijing",
    "beijing": "Beijing",
    "токио": "Tokyo",
    "tokyo": "Tokyo",
}

COUNTRY_ALIASES = {
    "китай": "China",
    "china": "China",
    "япония": "Japan",
    "japan": "Japan",
}


def parse_destination(destination: str) -> tuple[str, str]:
    if not destination:
        return "", ""
    parts = [part.strip() for part in destination.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return parts[0], ""


def normalize_location(value: str, aliases: dict[str, str]) -> str:
    if not value:
        return ""
    normalized = aliases.get(value.strip().lower())
    return normalized or value.strip()


def is_generic_title(title: str) -> bool:
    return title.strip().lower() in GENERIC_TITLES


def is_place_specific(place: dict) -> bool:
    title = str(place.get("title", "")).strip()
    if not title or is_generic_title(title):
        return False
    if float(place.get("confidence", 0) or 0) < 0.65:
        return False
    description = str(place.get("description", "")).strip().lower()
    if description.startswith("screenshot inspiration:"):
        return False
    city = str(place.get("city", "")).strip()
    if city and title.lower() == city.lower():
        return False
    return True


def title_looks_like_city_not_place(title: str, city: str, country: str) -> bool:
    normalized = title.strip().lower()
    if not normalized:
        return True
    if city and normalized == city.strip().lower():
        return True
    if country and normalized == country.strip().lower():
        return True
    return normalized in {value.lower() for value in CITY_ALIASES.values()} | {
        key.lower() for key in CITY_ALIASES
    }


def dedupe_places(places: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for place in places:
        title = str(place.get("title", "")).strip()
        if not title or is_generic_title(title):
            continue
        key = re.sub(r"\s+", " ", title.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(place)
    return unique
