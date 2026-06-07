"""Country metadata helpers for workspace creation."""

from datetime import datetime

COUNTRY_FLAGS: dict[str, str] = {
    "Japan": "🇯🇵",
    "Italy": "🇮🇹",
    "China": "🇨🇳",
    "France": "🇫🇷",
    "Spain": "🇪🇸",
    "Germany": "🇩🇪",
    "United Kingdom": "🇬🇧",
    "United States": "🇺🇸",
    "South Korea": "🇰🇷",
    "Thailand": "🇹🇭",
    "Vietnam": "🇻🇳",
    "Indonesia": "🇮🇩",
    "Turkey": "🇹🇷",
    "Greece": "🇬🇷",
    "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱",
    "Switzerland": "🇨🇭",
    "Austria": "🇦🇹",
    "Czech Republic": "🇨🇿",
    "Poland": "🇵🇱",
    "Mexico": "🇲🇽",
    "Brazil": "🇧🇷",
    "Argentina": "🇦🇷",
    "Morocco": "🇲🇦",
    "Egypt": "🇪🇬",
    "UAE": "🇦🇪",
    "Singapore": "🇸🇬",
    "India": "🇮🇳",
    "Australia": "🇦🇺",
    "Canada": "🇨🇦",
    "Norway": "🇳🇴",
    "Sweden": "🇸🇪",
    "Denmark": "🇩🇰",
    "Iceland": "🇮🇸",
    "Georgia": "🇬🇪",
    "Armenia": "🇦🇲",
}


def country_to_flag(country: str) -> str:
    return COUNTRY_FLAGS.get(country.strip(), "🌍")


def default_trip_name(country: str, year: int | None = None) -> str:
    return f"{country.strip()} {year or datetime.now().year}"


def parse_destination(destination: str) -> tuple[str, str]:
    if not destination:
        return "", ""
    parts = [part.strip() for part in destination.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""
