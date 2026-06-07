import uuid

from sqlalchemy.orm import Session

from app.agents.curator import extract_place_from_text
from app.db.models import PlaceModel, ReviewModel
from app.rag.store import search_places, upsert_place
from app.services.agent_log import log_agent_event
from app.services.geocoding import geocode_place
from app.services.tavily import tavily_service


async def enrich_place(db: Session, place: PlaceModel, workspace_id: str) -> PlaceModel:
    tools: list[str] = ["geocode_place"]
    verification, conf, snippet = tavily_service.verify_place(place.title, place.city)
    if tavily_service.available:
        tools.append("verify_place_status")
    else:
        verification = place.verification
        tools.append("verify_place_status")
        log_agent_event(
            db,
            workspace_id,
            "Researcher Agent",
            "Fallback",
            f"Web verification unavailable for {place.title} — saved as Unverified.",
            confidence=0.55,
            tools=["verify_place_status"],
            input_preview=place.title,
            output_preview="Saved as Unverified, will retry later.",
        )

    lat, lng, district = await geocode_place(place.title, place.city, place.country)
    if lat and lng:
        place.lat = lat
        place.lng = lng
        place.district = district

    if tavily_service.available:
        place.verification = verification
        place.confidence = max(place.confidence, conf) if verification == "Verified" else place.confidence

    similar = search_places(workspace_id, place.title, n=3)
    if similar:
        tools.append("rag_search")

    db.add(place)
    db.commit()
    upsert_place(place)

    log_agent_event(
        db,
        workspace_id,
        "Researcher Agent",
        "Success" if tavily_service.available else "Fallback",
        f"Enriched {place.title} with location and verification.",
        confidence=conf,
        tools=tools,
        input_preview=place.title,
        output_preview=f"{place.verification}, district={place.district}",
    )
    return place


def create_review_for_place(
    db: Session,
    workspace_id: str,
    place: PlaceModel,
    review_type: str,
    explanation: str,
    suggested_action: str,
) -> ReviewModel:
    review = ReviewModel(
        id=f"r{uuid.uuid4().hex[:10]}",
        workspace_id=workspace_id,
        type=review_type,
        title=place.title,
        city=place.city,
        country=place.country,
        category=place.category,
        confidence=place.confidence,
        explanation=explanation,
        source=place.source,
        suggested_action=suggested_action,
        image=place.image,
        place_ids=[place.id],
    )
    db.add(review)
    db.commit()
    return review
