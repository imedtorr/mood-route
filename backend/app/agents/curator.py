import asyncio
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.gigachat import PLACE_EXTRACTION_PROMPT, gigachat_service
from app.services.ollama import ollama_service

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


def detect_source(url: str) -> str:
    lower = url.lower()
    if "pinterest" in lower or "pin.it" in lower:
        return "Pinterest"
    if "instagram" in lower:
        return "Instagram"
    return "Article"


async def fetch_url_content(url: str) -> tuple[str, str, str]:
    """Returns title, text content, og image."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "MoodRoute/1.0"})
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return urlparse(url).netloc, "", ""

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc
    og_image = ""
    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name") or ""
        if "og:image" in prop.lower():
            og_image = meta.get("content", "")
            break
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")[:20]]
    text = " ".join(paragraphs)[:4000]
    return title, text, og_image


def _parse_destination(destination: str) -> tuple[str, str]:
    if not destination:
        return "", ""
    parts = [part.strip() for part in destination.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return parts[0], ""


def _normalize_location(value: str, aliases: dict[str, str]) -> str:
    if not value:
        return ""
    normalized = aliases.get(value.strip().lower())
    return normalized or value.strip()


def _is_meaningful_ocr(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 12:
        return False
    if re.fullmatch(r"[\d\s.,\[\]]+", cleaned):
        return False
    if re.search(r"\bids\b", cleaned, re.I):
        return False
    letters = sum(ch.isalpha() for ch in cleaned)
    return letters >= 8


def _is_generic_title(title: str) -> bool:
    return title.strip().lower() in GENERIC_TITLES


def _title_from_page_heading(page_title: str) -> str:
    if not page_title:
        return ""
    main = page_title.split("|")[0].split("—")[0].strip()
    if ":" in main:
        main = main.split(":")[0].strip()
    if len(main) < 3 or _is_generic_title(main):
        return ""
    return main[:80]


def _apply_page_title(extracted: dict, page_title: str) -> dict:
    candidate = _title_from_page_heading(page_title)
    if not candidate:
        return extracted
    current = str(extracted.get("title", "")).strip()
    if _is_generic_title(current) or extracted.get("confidence", 1) < 0.75:
        extracted = {**extracted, "title": candidate}
        if extracted.get("confidence", 0) < 0.75:
            extracted["confidence"] = min(0.78, float(extracted.get("confidence", 0.72)) + 0.05)
    return extracted


def _normalize_extracted(
    data: dict,
    image_hint: str = "",
    destination_hint: str = "",
) -> dict:
    default_city, default_country = _parse_destination(destination_hint)
    title = str(data.get("title", "")).strip()
    city = _normalize_location(str(data.get("city", "")).strip(), CITY_ALIASES) or default_city
    country = _normalize_location(str(data.get("country", "")).strip(), COUNTRY_ALIASES) or default_country
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    category = str(data.get("category", "Other")).strip() or "Other"
    confidence = float(data.get("confidence", 0.7) or 0.7)
    if not city or not country:
        confidence = min(confidence, 0.65)
    return {
        "title": title[:80] if title else "Discovered Place",
        "city": city,
        "country": country,
        "category": category,
        "tags": tags or ["Hidden Gem"],
        "description": str(data.get("description", "")).strip(),
        "aestheticNote": str(data.get("aestheticNote", "")).strip() or "A visually inspiring travel spot.",
        "confidence": confidence,
        "image": image_hint,
    }


async def extract_place_from_text(
    raw_text: str,
    source: str,
    note: str = "",
    image_hint: str = "",
    destination_hint: str = "",
    page_title: str = "",
) -> dict:
    context = [f"Source type: {source}"]
    if note:
        context.append(f"User note: {note}")
    if destination_hint:
        context.append(f"Trip destination hint: {destination_hint}")
    if page_title:
        context.append(f"Page title: {page_title}")
    prompt = f"""{PLACE_EXTRACTION_PROMPT}

{chr(10).join(context)}
Content:
{raw_text[:3000]}
"""
    if gigachat_service.available:
        response = gigachat_service.chat(
            prompt,
            system="You extract structured travel place data. Reply with JSON only.",
        )
        data = gigachat_service.parse_json(response)
        if data.get("title") and not _is_generic_title(str(data["title"])):
            return _apply_page_title(_normalize_extracted(data, image_hint, destination_hint), page_title)

    extracted = _heuristic_extract(raw_text, source, note, image_hint, destination_hint, page_title)
    return _apply_page_title(extracted, page_title)


async def extract_place_from_screenshot(
    file_path: str,
    source: str,
    note: str = "",
    image_hint: str = "",
    destination_hint: str = "",
) -> dict:
    if gigachat_service.available:
        vision_data = await asyncio.to_thread(
            gigachat_service.extract_place_from_image,
            file_path,
            source,
            note,
            destination_hint,
        )
        if vision_data.get("title") and not _is_generic_title(str(vision_data["title"])):
            return _normalize_extracted(vision_data, image_hint, destination_hint)

    ocr_text = await ollama_service.describe_image(file_path)
    if _is_meaningful_ocr(ocr_text):
        extracted = await extract_place_from_text(
            ocr_text,
            source,
            note,
            image_hint,
            destination_hint,
        )
        if not _is_generic_title(extracted.get("title", "")):
            return extracted

    return _heuristic_extract(
        ocr_text or f"Screenshot inspiration: {Path(file_path).name}",
        source,
        note,
        image_hint,
        destination_hint,
    )


def _heuristic_extract(
    raw_text: str,
    source: str,
    note: str,
    image_hint: str,
    destination_hint: str = "",
    page_title: str = "",
) -> dict:
    text = f"{raw_text} {note} {page_title}".lower()
    default_city, default_country = _parse_destination(destination_hint)

    city = default_city
    country = default_country
    for alias, normalized in CITY_ALIASES.items():
        if alias in text:
            city = normalized
            break
    for alias, normalized in COUNTRY_ALIASES.items():
        if alias in text:
            country = normalized
            break
    if city == "Tokyo" and "tokyo" not in text and default_city:
        city = default_city
    if country == "Japan" and "japan" not in text and "япония" not in text and default_country:
        country = default_country

    title = _title_from_page_heading(page_title)
    if not title:
        for pattern in (
            r"(?:заведение называется|called|named)\s+([A-Za-zА-Яа-я0-9][\w\s&'.-]{2,40})",
            r"([A-Za-z][\w\s&'.-]{2,30})\s+(?:cafe|café|coffee|roastery|bakery|restaurant|bar)",
            r"(?:matcha|cafe|coffee|museum|park|market)\s+[\w\s&'.-]{3,40}",
        ):
            match = re.search(pattern, raw_text + " " + note, re.I)
            if match:
                title = match.group(1).strip(" .,:;\"'")
                break
    if not title:
        title = "Discovered Place"

    category = "Other"
    if any(word in text for word in ("matcha", "coffee", "café", "cafe", "кофе", "чай", "tea")):
        category = "Cafe"
    elif "museum" in text or "музей" in text:
        category = "Museum"
    elif "park" in text or "garden" in text or "парк" in text:
        category = "Park"
    elif "market" in text or "рынок" in text:
        category = "Market"
    elif "neighborhood" in text or "район" in text:
        category = "Neighborhood"
    elif "restaurant" in text or "ресторан" in text:
        category = "Restaurant"

    tags = ["Hidden Gem"]
    if category == "Cafe":
        tags = ["Coffee Culture", "Cozy"]
    if "matcha" in text:
        tags.append("Matcha")

    return {
        "title": title[:80],
        "city": city,
        "country": country,
        "category": category,
        "tags": tags,
        "description": raw_text[:300] or f"Inspiration saved from {source}.",
        "aestheticNote": note or "A visually inspiring travel spot.",
        "confidence": 0.55 if city == "Unknown" or not city else 0.72,
        "image": image_hint,
    }
