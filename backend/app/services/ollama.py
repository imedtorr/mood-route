import base64
from pathlib import Path

import httpx

from app.config import settings


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_vision_model

    async def describe_image(self, image_path: str | Path) -> str:
        path = Path(image_path)
        if not path.exists():
            return ""
        image_b64 = base64.b64encode(path.read_bytes()).decode()
        payload = {
            "model": self.model,
            "prompt": (
                "Describe this travel inspiration image. Identify the place name, city, "
                "country if visible, type of location (cafe, museum, park, etc.), and aesthetic mood."
            ),
            "images": [image_b64],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "")
        except Exception:
            return ""

    async def available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


ollama_service = OllamaService()
