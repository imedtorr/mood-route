import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.prompts.extraction import (
    MULTI_PLACE_EXTRACTION_PROMPT,
    OCR_TRANSCRIPTION_PROMPT,
    PLACE_EXTRACTION_PROMPT,
    QUERY_EXTRACTION_PROMPT,
    VISION_EXTRACTION_PROMPT,
    build_extraction_prompt,
)
from app.services.llm_utils import parse_json, validate_extracted_place

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


async def init_ollama_client() -> None:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=180.0)


async def close_ollama_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def _get_client(*, timeout: float = 180.0) -> httpx.AsyncClient:
    if _http_client is not None:
        return _http_client
    return httpx.AsyncClient(timeout=timeout)


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.vision_model = settings.ollama_vision_model
        self.text_model = settings.ollama_text_model

    async def available(self) -> bool:
        return await self.is_available()

    @property
    def _vision_models(self) -> list[str]:
        fallbacks = [
            model.strip()
            for model in settings.ollama_vision_fallback_models.split(",")
            if model.strip()
        ]
        models = [self.vision_model, *fallbacks]
        unique: list[str] = []
        for model in models:
            if model not in unique:
                unique.append(model)
        return unique

    async def is_available(self) -> bool:
        try:
            client = _get_client(timeout=5.0)
            if client is _http_client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
            else:
                async with client:
                    resp = await client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("Ollama unavailable: %s", exc)
            return False

    async def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        json_mode: bool = False,
        images: list[str] | None = None,
        model: str | None = None,
    ) -> str:
        full_prompt = f"{system}\n\n{prompt}".strip() if system else prompt
        return await self._generate(
            model or self.text_model,
            full_prompt,
            images=images,
            json_mode=json_mode,
        )

    async def _generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
        *,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        if images:
            payload["images"] = images
        try:
            client = _get_client()
            if client is _http_client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            else:
                async with client:
                    resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as exc:
            logger.warning("Ollama generate failed (model=%s): %s", model, exc)
            return ""

    def _build_context(
        self,
        source: str,
        note: str,
        destination_hint: str,
        page_title: str = "",
    ) -> str:
        lines = [f"Source type: {source}"]
        if note:
            lines.append(f"User note: {note}")
        if destination_hint:
            lines.append(f"Trip destination hint: {destination_hint}")
        if page_title:
            lines.append(f"Page title: {page_title}")
        return "\n".join(lines)

    async def _image_b64(self, image_path: str | Path) -> str:
        return base64.b64encode(Path(image_path).read_bytes()).decode()

    async def _generate_vision(self, prompt: str, image_b64: str, *, json_mode: bool = False) -> str:
        for model in self._vision_models:
            response = await self._generate(model, prompt, images=[image_b64], json_mode=json_mode)
            if response.strip():
                return response.strip()
        return ""

    async def read_text_from_image(self, image_path: str | Path) -> str:
        path = Path(image_path)
        if not path.exists():
            return ""
        image_b64 = await self._image_b64(path)
        return await self._generate_vision(OCR_TRANSCRIPTION_PROMPT, image_b64)

    async def extract_place_from_image(
        self,
        image_path: str | Path,
        source: str = "Screenshot",
        note: str = "",
        destination_hint: str = "",
    ) -> dict[str, Any]:
        path = Path(image_path)
        if not path.exists():
            return {}
        image_b64 = await self._image_b64(path)
        context = self._build_context(source, note, destination_hint)
        prompt = build_extraction_prompt(VISION_EXTRACTION_PROMPT, context=context)
        response = await self._generate_vision(prompt, image_b64, json_mode=True)
        return validate_extracted_place(
            parse_json(response, context="vision_extraction")
        )

    async def extract_place_from_text(
        self,
        raw_text: str,
        source: str,
        note: str = "",
        destination_hint: str = "",
        page_title: str = "",
    ) -> dict[str, Any]:
        context = self._build_context(source, note, destination_hint, page_title)
        prompt = build_extraction_prompt(
            PLACE_EXTRACTION_PROMPT,
            context=context,
            content=raw_text[:3000],
        )
        response = await self._generate(self.text_model, prompt, json_mode=True)
        return validate_extracted_place(
            parse_json(response, context="text_extraction")
        )

    async def extract_places_from_text(
        self,
        raw_text: str,
        source: str,
        note: str = "",
        destination_hint: str = "",
        page_title: str = "",
    ) -> list[dict[str, Any]]:
        context = self._build_context(source, note, destination_hint, page_title)
        prompt = build_extraction_prompt(
            MULTI_PLACE_EXTRACTION_PROMPT,
            context=context,
            content=raw_text[:6000],
        )
        response = await self._generate(self.text_model, prompt, json_mode=True)
        data = parse_json(response, context="multi_place_extraction")
        places_raw = data.get("places")
        if isinstance(places_raw, list):
            return [
                validate_extracted_place(place)
                for place in places_raw
                if isinstance(place, dict) and place.get("title")
            ]
        return []

    async def extract_place_from_query(
        self,
        query: str,
        search_snippets: str,
        destination_hint: str = "",
        note: str = "",
    ) -> dict[str, Any]:
        context = self._build_context("Text", note, destination_hint)
        prompt = (
            f"{QUERY_EXTRACTION_PROMPT}\n\n{context}\n"
            f"User query: {query}\n\nSearch snippets:\n{search_snippets[:4000]}"
        )
        response = await self._generate(self.text_model, prompt, json_mode=True)
        return validate_extracted_place(
            parse_json(response, context="query_extraction")
        )


ollama_service = OllamaService()
