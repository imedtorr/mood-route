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


class LLMTask(str, Enum):
    PLACE_ENRICH = "place_enrich"
    ROUTE_NARRATIVE = "route_narrative"
    PLACE_EXTRACTION = "place_extraction"


class ExtractedPlace(BaseModel):
    title: str = ""
    city: str = ""
    country: str = ""
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
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        return []

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
