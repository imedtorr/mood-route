from app.config import settings


class TavilyService:
    def __init__(self) -> None:
        self._client = None
        if settings.tavily_api_key:
            try:
                from tavily import TavilyClient

                self._client = TavilyClient(api_key=settings.tavily_api_key)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def search(self, query: str, max_results: int = 3) -> list[dict]:
        if not self._client:
            return []
        try:
            result = self._client.search(query=query, max_results=max_results)
            return result.get("results", [])
        except Exception:
            return []

    def verify_place(self, name: str, city: str) -> tuple[str, float, str]:
        """Returns verification status, confidence, snippet."""
        if not self._client:
            return "Unverified", 0.5, "Web verification unavailable"
        query = f"{name} {city} opening hours closed permanently 2025 2026"
        results = self.search(query, max_results=2)
        if not results:
            return "Needs Recheck", 0.6, "No search results found"
        snippet = " ".join(r.get("content", "")[:200] for r in results)
        lower = snippet.lower()
        if any(w in lower for w in ("permanently closed", "closed down", "shut down")):
            return "Needs Recheck", 0.75, snippet
        if any(w in lower for w in ("open", "hours", "visit", "located")):
            return "Verified", 0.88, snippet
        return "Needs Recheck", 0.65, snippet


tavily_service = TavilyService()
