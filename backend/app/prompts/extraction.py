from app.services.llm_utils import PLACE_CATEGORIES_STR

PLACE_EXTRACTION_PROMPT = f"""Extract travel place information from this content.
Return JSON with keys: title, city, country, category (one of {PLACE_CATEGORIES_STR}), tags (array of aesthetic tags like Coffee Culture, Minimal, Cozy, Matcha), description, aestheticNote, confidence (0-1).

Read all visible text including Russian, Chinese, and English. Extract the venue name, address, city, and country if present."""

MULTI_PLACE_EXTRACTION_PROMPT = f"""Extract ALL distinct travel places mentioned in this content.
Return JSON with key "places" — an array of objects. Each object must have keys:
title, city, country, category (one of {PLACE_CATEGORIES_STR}),
tags (array), description, aestheticNote, confidence (0-1).

If only one place is present, still return it inside the "places" array.
Do not invent places that are not mentioned."""

VISION_EXTRACTION_PROMPT = f"""Extract travel place information from this screenshot or photo.
Return JSON with keys: title, city, country, category (one of {PLACE_CATEGORIES_STR}), tags (array), description, aestheticNote, confidence (0-1).

Rules:
- title must be the SPECIFIC venue, town, or landmark (e.g. ZHUJIAJIAO), NOT a major city (e.g. Shanghai)
- If text says "ancient town ZHUJIAJIAO near Shanghai" / "древний город ZHUJIAJIAO вблизи Шанхая", use title=ZHUJIAJIAO, city=Shanghai, country=China
- Read ALL overlay text on collages: Russian, Chinese, English, Latin
- Use description from visible text; do not invent facts about unrelated landmarks
- If no specific place name is visible, return {{"title": "", "confidence": 0}}"""

OCR_TRANSCRIPTION_PROMPT = """Transcribe ALL visible text on this travel inspiration image.
Include Russian, English, Chinese, and Latin script exactly as written.
Preserve place names (e.g. ZHUJIAJIAO, 朱家角). Return plain text only, no commentary."""

QUERY_EXTRACTION_PROMPT = """Using the user query and web search snippets below, build a travel place card.
Return JSON with keys: title, city, country, category, tags (array), description, aestheticNote, confidence (0-1).
Base facts on the snippets; do not invent a closed or fictional venue."""


def build_extraction_prompt(
    template: str,
    *,
    context: str,
    content: str = "",
) -> str:
    parts = [template, "", context]
    if content:
        parts.extend(["Content:", content])
    return "\n".join(parts)
