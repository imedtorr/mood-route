import asyncio
import html
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.domain.places import (
    CITY_ALIASES,
    COUNTRY_ALIASES,
    dedupe_places,
    is_generic_title,
    is_place_specific,
    normalize_location,
    parse_destination,
    title_looks_like_city_not_place,
)
from app.services.llm_utils import normalize_aesthetic_tags
from app.services.ocr import extract_text_from_image, normalize_place_name
from app.services.ollama import ollama_service
from app.services.tavily import tavily_service

BLOCKED_URL_HOSTS = ("instagram.com", "pinterest.com", "pin.it")


def is_blocked_social_url(url: str) -> bool:
    lower = url.lower()
    return any(host in lower for host in BLOCKED_URL_HOSTS)


def detect_source(url: str) -> str:
    return "Article"


async def fetch_url_content(url: str) -> tuple[str, str, str]:
    """Returns title, text content, og image."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; MoodRoute/1.0)"},
            )
            resp.raise_for_status()
            page_html = resp.text
    except Exception:
        return urlparse(url).netloc, "", ""

    title = urlparse(url).netloc
    og_image = ""
    text = ""

    try:
        import trafilatura

        downloaded = trafilatura.extract(
            page_html,
            include_comments=False,
            include_tables=False,
            output_format="txt",
        )
        meta = trafilatura.extract_metadata(page_html)
        if meta and meta.title:
            title = meta.title
        if downloaded:
            text = downloaded[:6000]
    except Exception:
        pass

    if not text.strip():
        soup = BeautifulSoup(page_html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else title
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")[:20]]
        text = " ".join(paragraphs)[:4000]

    soup = BeautifulSoup(page_html, "html.parser")
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        content = meta.get("content", "")
        if "og:image" in prop and not og_image:
            og_image = html.unescape(content)

    return title, text, og_image


def _is_meaningful_ocr(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 12:
        return False
    if re.fullmatch(r"[\d\s.,\[\]]+", cleaned):
        return False
    letters = sum(ch.isalpha() for ch in cleaned)
    return letters >= 8


def _is_valid_vision_extract(data: dict) -> bool:
    title = str(data.get("title", "")).strip()
    if not title or is_generic_title(title):
        return False
    city = str(data.get("city", "")).strip()
    country = str(data.get("country", "")).strip()
    if title_looks_like_city_not_place(title, city, country):
        return False
    return True


def _title_from_page_heading(page_title: str) -> str:
    if not page_title:
        return ""
    main = page_title.split("|")[0].split("—")[0].strip()
    if ":" in main:
        main = main.split(":")[0].strip()
    if len(main) < 3 or is_generic_title(main):
        return ""
    if len(main) > 60:
        return ""
    return main[:80]


def _apply_page_title(extracted: dict, page_title: str) -> dict:
    candidate = _title_from_page_heading(page_title)
    if not candidate:
        return extracted
    current = str(extracted.get("title", "")).strip()
    if is_generic_title(current) or extracted.get("confidence", 1) < 0.75:
        extracted = {**extracted, "title": candidate}
        if extracted.get("confidence", 0) < 0.75:
            extracted["confidence"] = min(0.78, float(extracted.get("confidence", 0.72)) + 0.05)
    return extracted


def _normalize_extracted(
    data: dict,
    image_hint: str = "",
    destination_hint: str = "",
) -> dict:
    default_city, default_country = parse_destination(destination_hint)
    title = str(data.get("title", "")).strip()
    city = normalize_location(str(data.get("city", "")).strip(), CITY_ALIASES) or default_city
    country = (
        normalize_location(str(data.get("country", "")).strip(), COUNTRY_ALIASES) or default_country
    )
    tags = normalize_aesthetic_tags(data.get("tags") or [], allow_custom=False)
    category = str(data.get("category", "Other")).strip() or "Other"
    confidence = float(data.get("confidence", 0.7) or 0.7)
    if not city or not country:
        confidence = min(confidence, 0.65)
    return {
        "title": title[:80] if title else "Discovered Place",
        "city": city,
        "country": country,
        "category": category,
        "tags": tags,
        "description": str(data.get("description", "")).strip(),
        "aestheticNote": str(data.get("aestheticNote", "")).strip() or "A visually inspiring travel spot.",
        "confidence": confidence,
        "image": image_hint,
    }


async def extract_places_from_text(
    raw_text: str,
    source: str,
    note: str = "",
    image_hint: str = "",
    destination_hint: str = "",
    page_title: str = "",
    *,
    apply_page_title: bool = True,
) -> list[dict]:
    if await ollama_service.available():
        places_raw = await ollama_service.extract_places_from_text(
            raw_text, source, note, destination_hint, page_title
        )
        if places_raw:
            places = [
                _normalize_extracted(item, image_hint, destination_hint)
                for item in places_raw
            ]
            places = dedupe_places(places)
            if places:
                if apply_page_title and len(places) == 1:
                    places[0] = _apply_page_title(places[0], page_title)
                return places

    single = await extract_place_from_text(
        raw_text,
        source,
        note,
        image_hint,
        destination_hint,
        page_title,
        apply_page_title=apply_page_title,
    )
    return [single] if single.get("title") else []


async def extract_place_from_text(
    raw_text: str,
    source: str,
    note: str = "",
    image_hint: str = "",
    destination_hint: str = "",
    page_title: str = "",
    *,
    apply_page_title: bool = True,
) -> dict:
    if await ollama_service.available():
        data = await ollama_service.extract_place_from_text(
            raw_text, source, note, destination_hint, page_title
        )
        if data.get("title") and not is_generic_title(str(data["title"])):
            normalized = _normalize_extracted(data, image_hint, destination_hint)
            if apply_page_title:
                normalized = _apply_page_title(normalized, page_title)
            return normalized

    extracted = _heuristic_extract(raw_text, source, note, image_hint, destination_hint, page_title)
    if apply_page_title:
        extracted = _apply_page_title(extracted, page_title)
    return extracted


async def extract_place_from_screenshot(
    file_path: str,
    source: str,
    note: str = "",
    image_hint: str = "",
    destination_hint: str = "",
) -> dict:
    ocr_text = await asyncio.to_thread(extract_text_from_image, file_path)

    if _is_meaningful_ocr(ocr_text) and await ollama_service.available():
        text_extracted = await extract_place_from_text(
            ocr_text,
            source,
            note,
            image_hint,
            destination_hint,
            apply_page_title=False,
        )
        if is_place_specific(text_extracted):
            return text_extracted

    if _is_meaningful_ocr(ocr_text):
        extracted = _heuristic_extract(
            ocr_text,
            source,
            note,
            image_hint,
            destination_hint,
        )
        if not is_generic_title(extracted.get("title", "")):
            return extracted

    if await ollama_service.available():
        vision_data = await ollama_service.extract_place_from_image(
            file_path, source, note, destination_hint
        )
        if _is_valid_vision_extract(vision_data):
            return _normalize_extracted(vision_data, image_hint or str(file_path), destination_hint)

        if not _is_meaningful_ocr(ocr_text):
            ocr_text = await ollama_service.read_text_from_image(file_path)
            if _is_meaningful_ocr(ocr_text):
                text_extracted = await extract_place_from_text(
                    ocr_text,
                    source,
                    note,
                    image_hint,
                    destination_hint,
                    apply_page_title=False,
                )
                if is_place_specific(text_extracted):
                    return text_extracted
                extracted = _heuristic_extract(
                    ocr_text, source, note, image_hint, destination_hint
                )
                if not is_generic_title(extracted.get("title", "")):
                    return extracted

    return _heuristic_extract(
        f"Screenshot inspiration: {Path(file_path).name}",
        source,
        note,
        image_hint,
        destination_hint,
    )


async def extract_place_from_query(
    query: str,
    note: str = "",
    destination_hint: str = "",
) -> dict:
    search_query = f"{query} {destination_hint} travel guide".strip()
    snippets = ""
    if tavily_service.available:
        results = tavily_service.search(search_query, max_results=4)
        snippets = "\n\n".join(
            f"{r.get('title', '')}: {r.get('content', '')[:400]}" for r in results
        )

    if await ollama_service.available() and snippets:
        data = await ollama_service.extract_place_from_query(
            query, snippets, destination_hint, note
        )
        if data.get("title") and not is_generic_title(str(data["title"])):
            return _normalize_extracted(data, "", destination_hint)

    default_city, default_country = parse_destination(destination_hint)
    return _normalize_extracted(
        {
            "title": query[:80],
            "city": default_city or "Unknown",
            "country": default_country or "Unknown",
            "category": "Other",
            "tags": ["Hidden Gem"],
            "description": snippets[:300] if snippets else f"Place lookup: {query}",
            "aestheticNote": note or "Added from place name search.",
            "confidence": 0.6 if snippets else 0.5,
        },
        "",
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
    default_city, default_country = parse_destination(destination_hint)

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

    combined = raw_text + " " + note
    title = _title_from_page_heading(page_title)
    if not title:
        for pattern in (
            r"(?:древн(?:ий|его)\s+город|ancient\s+town(?:\s+of)?)\s+([A-Z][A-Za-z][\w'-]{1,35})",
            r"(?:город|town)\s+([A-Z][A-Za-z][\w'-]{1,35})",
            r"(?:заведение называется|called|named)\s+([A-Za-zА-Яа-я0-9][\w\s&'.-]{2,40})",
            r"([A-Za-z][\w\s&'.-]{2,30})\s+(?:cafe|café|coffee|roastery|bakery|restaurant|bar)",
            r"((?:matcha|cafe|coffee|museum|park|market)\s+[\w\s&'.-]{3,40})",
        ):
            match = re.search(pattern, combined, re.I)
            if match:
                title = normalize_place_name(match.group(1).strip(" .,:;\"'"))
                break
    if not title:
        quoted = re.search(r"«([^»]{3,60})»", combined)
        if quoted:
            title = quoted.group(1).strip()
    if not title:
        title = "Discovered Place"

    category = "Other"
    if any(word in text for word in ("водный город", "канал", "water town", "waterfront", "canal")):
        category = "Waterfront"
    elif any(word in text for word in ("matcha", "coffee", "café", "cafe", "кофе", "чай", "tea")):
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
    elif any(word in text for word in ("город", "town", "venice", "венеция")):
        category = "Waterfront"

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
        "confidence": (
            0.45
            if is_generic_title(title) or raw_text.startswith("Screenshot inspiration:")
            else 0.55 if city == "Unknown" or not city else 0.72
        ),
        "image": image_hint,
    }
