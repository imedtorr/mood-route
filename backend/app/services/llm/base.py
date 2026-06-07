from typing import Any, Protocol, runtime_checkable

from app.services.llm_utils import LLMTask, parse_json, validate_extracted_place

__all__ = ["LLMClient", "LLMTask", "parse_json", "validate_extracted_place"]


@runtime_checkable
class LLMClient(Protocol):
    @property
    def available(self) -> bool: ...

    async def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        json_mode: bool = False,
        images: list[str] | None = None,
    ) -> str: ...
