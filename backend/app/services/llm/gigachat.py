import asyncio
import json
import logging
import re
from typing import Any

from app.config import settings
from app.domain.places import is_place_specific
from app.prompts.enrichment import (
    PLACE_CARD_ENRICH_PROMPT,
    PLACE_CARD_WEB_ENRICH_PROMPT,
    build_route_narrative_prompt,
)
from app.services.llm_utils import LLMTask, merge_enrich_into_place, parse_json

logger = logging.getLogger(__name__)


class GigaChatService:
    def __init__(self) -> None:
        self._client = None
        if settings.gigachat_credentials:
            try:
                from gigachat import GigaChat

                self._client = GigaChat(
                    credentials=settings.gigachat_credentials,
                    verify_ssl_certs=False,
                )
            except Exception as exc:
                logger.warning("GigaChat init failed: %s", exc)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, prompt: str, system: str = "", *, task: LLMTask | None = None) -> str:
        if not self._client:
            return self._fallback(task, prompt)
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = self._client.chat({"messages": messages})
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("GigaChat chat failed: %s", exc)
            return self._fallback(task, prompt)

    async def achat(self, prompt: str, system: str = "", *, task: LLMTask | None = None) -> str:
        return await asyncio.to_thread(self.chat, prompt, system, task=task)

    def enrich_place_card(self, place: dict[str, Any], destination_hint: str = "") -> dict[str, Any]:
        if not self._client:
            return place
        if not is_place_specific(place):
            return place
        context = json.dumps(place, ensure_ascii=False)
        hint = f"\nTrip destination: {destination_hint}" if destination_hint else ""
        prompt = f"{PLACE_CARD_ENRICH_PROMPT}{hint}\n\nRaw data:\n{context}"
        response = self.chat(
            prompt,
            system="You polish travel place cards. Reply with JSON only.",
            task=LLMTask.PLACE_ENRICH,
        )
        data = parse_json(response, context="place_enrich")
        return merge_enrich_into_place(place, data)

    async def enrich_place_card_async(
        self,
        place: dict[str, Any],
        destination_hint: str = "",
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self.enrich_place_card, place, destination_hint)

    def enrich_place_card_with_web(
        self,
        place: dict[str, Any],
        web_context: str = "",
        destination_hint: str = "",
    ) -> dict[str, Any]:
        if not self._client:
            return place
        context = json.dumps(place, ensure_ascii=False)
        hint = f"\nTrip destination: {destination_hint}" if destination_hint else ""
        web_block = f"\n\nWeb search results:\n{web_context}" if web_context.strip() else ""
        prompt = f"{PLACE_CARD_WEB_ENRICH_PROMPT}{hint}\n\nRaw data:\n{context}{web_block}"
        response = self.chat(
            prompt,
            system="You enrich travel place cards using web research. Reply with JSON only.",
            task=LLMTask.PLACE_ENRICH,
        )
        data = parse_json(response, context="place_web_enrich")
        return merge_enrich_into_place(place, data)

    async def enrich_place_card_with_web_async(
        self,
        place: dict[str, Any],
        web_context: str = "",
        destination_hint: str = "",
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.enrich_place_card_with_web,
            place,
            web_context,
            destination_hint,
        )

    def generate_route_narrative(
        self,
        city: str,
        days: int,
        day_stops: list[list[str]],
        aesthetic_mode: bool,
    ) -> dict[str, Any]:
        if not self._client:
            return self._fallback_dict(LLMTask.ROUTE_NARRATIVE, days)
        prompt = build_route_narrative_prompt(city, days, day_stops, aesthetic_mode)
        response = self.chat(
            prompt,
            system="You write travel itineraries. Reply with JSON only.",
            task=LLMTask.ROUTE_NARRATIVE,
        )
        data = parse_json(response, context="route_narrative")
        return data if data else self._fallback_dict(LLMTask.ROUTE_NARRATIVE, days)

    async def generate_route_narrative_async(
        self,
        city: str,
        days: int,
        day_stops: list[list[str]],
        aesthetic_mode: bool,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.generate_route_narrative,
            city,
            days,
            day_stops,
            aesthetic_mode,
        )

    async def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        json_mode: bool = False,
        images: list[str] | None = None,
    ) -> str:
        if images:
            logger.warning("GigaChat does not support images; ignoring images parameter")
        _ = json_mode
        return await self.achat(prompt, system)

    def _fallback(self, task: LLMTask | None, prompt: str) -> str:
        resolved = task or self._infer_task(prompt)
        if resolved == LLMTask.ROUTE_NARRATIVE:
            days = self._extract_days_from_prompt(prompt)
            return json.dumps(self._fallback_dict(LLMTask.ROUTE_NARRATIVE, days))
        if resolved == LLMTask.PLACE_ENRICH:
            return "{}"
        return "OK"

    def _fallback_dict(self, task: LLMTask, days: int = 4) -> dict[str, Any]:
        if task == LLMTask.ROUTE_NARRATIVE:
            return {
                "dayThemes": ["Curated day"] * max(days, 1),
                "routeSummary": "Grouped by neighborhood to reduce travel time.",
            }
        return {}

    def _infer_task(self, prompt: str) -> LLMTask:
        lower = prompt.lower()
        if "daythemes" in lower or "routesummary" in lower:
            return LLMTask.ROUTE_NARRATIVE
        if "polish" in lower or "place card" in lower:
            return LLMTask.PLACE_ENRICH
        return LLMTask.PLACE_EXTRACTION

    def _extract_days_from_prompt(self, prompt: str) -> int:
        match = re.search(r"(\d+)-day trip", prompt, re.I)
        if match:
            return max(int(match.group(1)), 1)
        return 4


gigachat_service = GigaChatService()
