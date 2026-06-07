PLACE_CARD_ENRICH_PROMPT = """You polish a travel place card for a knowledge base.
Given raw extracted data, improve description, aestheticNote, tags, and category.

Rules:
- Keep title, city, country unchanged
- Describe ONLY the specific place in title — never write a generic city guide
- Base description and aestheticNote ONLY on facts in the raw data; do not invent landmarks
- If raw data lacks detail, keep description short and factual

Return JSON with keys: title, city, country, category, tags (array), description, aestheticNote, confidence (0-1)."""


def build_route_narrative_prompt(
    city: str,
    days: int,
    day_stops: list[list[str]],
    aesthetic_mode: bool,
) -> str:
    stops_summary = "\n".join(
        f"Day {index + 1}: {', '.join(stops)}" for index, stops in enumerate(day_stops)
    )
    return f"""Create a poetic travel narrative for a {days}-day trip in {city}.
Aesthetic mode: {aesthetic_mode}

Stops per day:
{stops_summary}

Return JSON with keys:
- dayThemes: array of {days} short theme strings (one per day)
- routeSummary: one sentence summarizing the overall route philosophy"""
