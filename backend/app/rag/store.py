import logging
from pathlib import Path

import chromadb

from app.config import settings
from app.db.models import PlaceModel
from app.rag.embeddings import embed_text, embed_texts

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None


def get_chroma() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def collection_name(workspace_id: str) -> str:
    return f"ws_{workspace_id}"


def place_document(p: PlaceModel) -> str:
    return " | ".join(
        [
            p.title,
            p.city,
            p.country,
            p.category,
            ", ".join(p.tags),
            p.aesthetic_note,
            p.description,
            p.reason,
            p.district,
        ]
    )


def upsert_place(p: PlaceModel) -> None:
    client = get_chroma()
    col = client.get_or_create_collection(collection_name(p.workspace_id))
    doc = place_document(p)
    col.upsert(
        ids=[p.id],
        documents=[doc],
        embeddings=[embed_text(doc)],
        metadatas=[{"title": p.title, "city": p.city, "category": p.category}],
    )


def delete_place(workspace_id: str, place_id: str) -> None:
    client = get_chroma()
    try:
        col = client.get_collection(collection_name(workspace_id))
        col.delete(ids=[place_id])
    except Exception:
        pass


def delete_workspace_collection(workspace_id: str) -> None:
    client = get_chroma()
    try:
        client.delete_collection(collection_name(workspace_id))
    except Exception:
        pass


def search_places(workspace_id: str, query: str, n: int = 5) -> list[tuple[str, float]]:
    client = get_chroma()
    try:
        col = client.get_collection(collection_name(workspace_id))
    except Exception:
        return []
    if col.count() == 0:
        return []
    results = col.query(query_embeddings=[embed_text(query)], n_results=min(n, col.count()))
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    return [(pid, 1 - d) for pid, d in zip(ids, distances)]


def bulk_upsert_places(places: list[PlaceModel]) -> None:
    if not places:
        return
    ws_id = places[0].workspace_id
    client = get_chroma()
    col = client.get_or_create_collection(collection_name(ws_id))
    docs = [place_document(p) for p in places]
    col.upsert(
        ids=[p.id for p in places],
        documents=docs,
        embeddings=embed_texts(docs),
        metadatas=[{"title": p.title, "city": p.city} for p in places],
    )
