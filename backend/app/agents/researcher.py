import uuid

from sqlalchemy.orm import Session

from app.domain.places import is_place_specific
from app.db.models import PlaceModel, ReviewModel
from app.rag.store import search_places, upsert_place
from app.services.agent_log import log_agent_event
from app.services.geocoding import geocode_place
from app.services.tavily import tavily_service


async def enrich_place(db: Session, place: PlaceModel, workspace_id: str) -> PlaceModel:
    tools: list[str] = ["geocode_place"]
    place_dict = {
        "title": place.title,
        "city": place.city,
        "country": place.country,
        "confidence": place.confidence,
        "description": place.description,
    }
    specific = is_place_specific(place_dict)

    if specific and tavily_service.available:
        verification, conf, snippet = tavily_service.verify_place(place.title, place.city)
        tools.append("verify_place_status")
    elif tavily_service.available:
        verification, conf, snippet = "Unverified", 0.5, ""
        tools.append("verify_place_status")
        log_agent_event(
            db,
            workspace_id,
            "Researcher Agent",
            "Needs Review",
            f"Skipped web verification for imprecise title '{place.title}'.",
            confidence=place.confidence,
            tools=["verify_place_status"],
            input_preview=place.title,
            output_preview="Unverified — needs manual review",
        )
    else:
        verification = place.verification
        conf = place.confidence
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

    geocode_title = place.title if specific else f"{place.title} {place.city}".strip()
    lat, lng, district = await geocode_place(geocode_title, place.city, place.country)
    if lat and lng:
        place.lat = lat
        place.lng = lng
        place.district = district

    if tavily_service.available:
        place.verification = verification
        if specific and verification == "Verified":
            place.confidence = max(place.confidence, conf)
        elif not specific:
            place.confidence = min(place.confidence, 0.55)

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
