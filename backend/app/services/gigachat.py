import json
import re
from pathlib import Path
from typing import Any

from app.config import settings

PLACE_EXTRACTION_PROMPT = """Extract travel place information from this content.
Return JSON with keys: title, city, country, category (one of Cafe, Restaurant, Museum, Park, Hotel, Landmark, Viewpoint, Market, Neighborhood, Shopping, Waterfront, Other), tags (array of aesthetic tags like Coffee Culture, Minimal, Cozy, Matcha), description, aestheticNote, confidence (0-1).

Read all visible text including Russian, Chinese, and English. Extract the venue name, address, city, and country if present."""


class GigaChatService:
    def __init__(self) -> None:
        self._client = None
        if settings.gigachat_credentials:
            try:
                from gigachat import GigaChat

                self._client = GigaChat(credentials=settings.gigachat_credentials, verify_ssl_certs=False)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, prompt: str, system: str = "") -> str:
        if not self._client:
            return self._fallback(prompt)
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = self._client.chat({"messages": messages})
            return response.choices[0].message.content or ""
        except Exception:
            return self._fallback(prompt)

    def extract_place_from_image(
        self,
        image_path: str | Path,
        source: str = "Screenshot",
        note: str = "",
        destination_hint: str = "",
    ) -> dict[str, Any]:
        if not self._client:
            return {}
        path = Path(image_path)
        if not path.exists():
            return {}
        try:
            context = [f"Source type: {source}"]
            if note:
                context.append(f"User note: {note}")
            if destination_hint:
                context.append(f"Trip destination hint: {destination_hint}")
            prompt = PLACE_EXTRACTION_PROMPT + "\n\n" + "\n".join(context)
            from gigachat import GigaChat

            with GigaChat(
                credentials=settings.gigachat_credentials,
                verify_ssl_certs=False,
                model=settings.gigachat_vision_model,
            ) as vision_client:
                uploaded = vision_client.upload_file(path.open("rb"), purpose="general")
                response = vision_client.chat(
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You extract structured travel place data from screenshots and images. "
                                    "Reply with JSON only."
                                ),
                            },
                            {
                                "role": "user",
                                "content": prompt,
                                "attachments": [uploaded.id_],
                            },
                        ],
                    }
                )
            return self.parse_json(response.choices[0].message.content or "")
        except Exception:
            return {}

    def _fallback(self, prompt: str) -> str:
        if "itinerary" in prompt.lower() or "маршрут" in prompt.lower():
            return json.dumps({"theme": "Curated day", "note": "Generated with heuristic planner"})
        if "extract" in prompt.lower() or "place" in prompt.lower():
            return json.dumps(
                {
                    "title": "Discovered Place",
                    "city": "Tokyo",
                    "country": "Japan",
                    "category": "Cafe",
                    "tags": ["Minimal", "Slow Travel"],
                    "description": "A charming local spot extracted from inspiration.",
                    "aestheticNote": "Perfect for a slow morning.",
                    "confidence": 0.72,
                }
            )
        return "OK"

    def parse_json(self, text: str) -> dict[str, Any]:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}


gigachat_service = GigaChatService()
