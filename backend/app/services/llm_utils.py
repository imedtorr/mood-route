import json
import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

PLACE_CATEGORIES = (
    "Cafe",
    "Restaurant",
    "Museum",
    "Park",
    "Hotel",
    "Landmark",
    "Viewpoint",
    "Market",
    "Neighborhood",
    "Shopping",
    "Waterfront",
    "Other",
)

PLACE_CATEGORIES_STR = ", ".join(PLACE_CATEGORIES)

AESTHETIC_TAGS = (
    "Architecture",
    "Coffee Culture",
    "Cozy",
    "Creative",
    "Hidden Gem",
    "Luxury",
    "Matcha",
    "Minimal",
    "Neon",
    "Photography",
    "Slow Travel",
    "Vintage",
)

AESTHETIC_TAGS_STR = ", ".join(AESTHETIC_TAGS)

_CANONICAL_BY_LOWER = {tag.lower(): tag for tag in AESTHETIC_TAGS}

_AESTHETIC_TAG_ALIASES: dict[str, str] = {
    "hidden gems": "Hidden Gem",
    "hidden-gem": "Hidden Gem",
    "must see": "Hidden Gem",
    "coffee": "Coffee Culture",
    "coffee shop": "Coffee Culture",
    "cafe culture": "Coffee Culture",
    "dessert cafe": "Coffee Culture",
    "minimalist": "Minimal",
    "minimalism": "Minimal",
    "open concept": "Minimal",
    "photo": "Photography",
    "photos": "Photography",
    "panoramic views": "Photography",
    "skyline": "Photography",
    "cityscape": "Photography",
    "cityscape view": "Photography",
    "river view": "Photography",
    "daylight experience": "Photography",
    "neon lights": "Neon",
    "nighttime": "Neon",
    "urban": "Neon",
    "slow-travel": "Slow Travel",
    "matcha tea": "Matcha",
    "architectural": "Architecture",
    "modern architecture": "Architecture",
    "traditional architecture": "Architecture",
    "architectural marvel": "Architecture",
    "cozy vibe": "Cozy",
    "homely atmosphere": "Cozy",
    "elegant ambiance": "Cozy",
    "indoor garden": "Cozy",
    "gardening": "Cozy",
    "creative space": "Creative",
    "art": "Creative",
    "art concept space": "Creative",
    "optical art": "Creative",
    "folk art": "Creative",
    "visual inspiration": "Creative",
    "craftsmanship": "Creative",
    "unique design": "Creative",
    "cultural hub": "Creative",
    "croissant gym theme": "Creative",
    "luxurious": "Luxury",
    "luxury stay": "Luxury",
    "luxury experience": "Luxury",
    "modern luxury": "Luxury",
    "elegant metropolis": "Luxury",
    "fashion": "Luxury",
    "vintage style": "Vintage",
    "historical": "Vintage",
    "historical charm": "Vintage",
    "historical landmark": "Vintage",
    "historical water town": "Vintage",
    "cultural heritage": "Vintage",
    "traditional": "Vintage",
    "traditional craft": "Vintage",
    "picturesque canals": "Slow Travel",
}


def _resolve_aesthetic_tag(raw: str) -> str | None:
    cleaned = raw.strip()
    if not cleaned:
        return None
    lower = cleaned.lower()
    if lower in _CANONICAL_BY_LOWER:
        return _CANONICAL_BY_LOWER[lower]
    return _AESTHETIC_TAG_ALIASES.get(lower)


def normalize_aesthetic_tags(tags: Any, *, allow_custom: bool = False) -> list[str]:
    if isinstance(tags, str):
        raw_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    elif isinstance(tags, list):
        raw_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    else:
        raw_tags = []

    result: list[str] = []
    seen: set[str] = set()

    for raw in raw_tags:
        canonical = _resolve_aesthetic_tag(raw)
        if canonical:
            if canonical not in seen:
                result.append(canonical)
                seen.add(canonical)
        elif allow_custom and raw not in seen:
            result.append(raw)
            seen.add(raw)

    if not result and not allow_custom:
        return ["Hidden Gem"]
    return result[:6]


class LLMTask(str, Enum):
    PLACE_ENRICH = "place_enrich"
    ROUTE_NARRATIVE = "route_narrative"
    PLACE_EXTRACTION = "place_extraction"


class ExtractedPlace(BaseModel):
    title: str = ""
    city: str = ""
    country: str = ""
    address: str = ""
    category: str = "Other"
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    aestheticNote: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    image: str = ""

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value if value in PLACE_CATEGORIES else "Other"

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> list[str]:
        return normalize_aesthetic_tags(value, allow_custom=False)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


def _extract_balanced_json(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def parse_json(text: str, *, context: str = "") -> dict[str, Any]:
    if not text or not text.strip():
        if context:
            logger.warning("Empty LLM response (%s)", context)
        return {}

    candidates: list[str] = []
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        candidates.append(fenced.group(1).strip())
    balanced = _extract_balanced_json(text)
    if balanced:
        candidates.append(balanced)
    candidates.append(text.strip())

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    if context:
        logger.warning("Failed to parse JSON from LLM response (%s): %.200s", context, text)
    return {}


def validate_extracted_place(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    try:
        return ExtractedPlace.model_validate(data).to_dict()
    except Exception as exc:
        logger.warning("ExtractedPlace validation failed: %s", exc)
        return data


def normalize_enrich_response(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    if "aesthetic_note" in data and "aestheticNote" not in data:
        data = {**data, "aestheticNote": data["aesthetic_note"]}
    return validate_extracted_place(data)


def merge_enrich_into_place(place: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_enrich_response(data)
    if not normalized:
        return place
    merged = {**place}
    for key in ("description", "aestheticNote", "tags", "category", "confidence"):
        value = normalized.get(key)
        if value:
            merged[key] = value
    return merged
