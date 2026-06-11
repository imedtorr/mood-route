import uuid

from sqlalchemy.orm import Session

from app.domain.places import is_place_specific
from app.db.models import PlaceModel, ReviewModel
from app.rag.store import search_places, upsert_place
from app.services.agent_log import log_agent_event, new_run_id
from app.services.geocoding import geocode_place
from app.services.gigachat import gigachat_service
from app.services.llm_utils import normalize_aesthetic_tags
from app.services.tavily import tavily_service


def _geocode_title(place: PlaceModel) -> str:
    place_dict = {
        "title": place.title,
        "city": place.city,
        "country": place.country,
        "confidence": place.confidence,
        "description": place.description,
    }
    specific = is_place_specific(place_dict)
    return place.title if specific else f"{place.title} {place.city}".strip()


async def ensure_place_geocoded(
    db: Session,
    place: PlaceModel,
    workspace_id: str | None = None,
    *,
    force: bool = False,
    run_id: str | None = None,
) -> PlaceModel:
    if not force and place.lat is not None and place.lng is not None:
        return place

    geocode_title = _geocode_title(place)
    lat, lng, district, resolved_address = await geocode_place(
        geocode_title,
        place.city,
        place.country,
        place.address or "",
        place.category,
    )
    if lat is not None and lng is not None:
        place.lat = lat
        place.lng = lng
        place.district = district
        if resolved_address and not place.address:
            place.address = resolved_address
        db.add(place)
        db.commit()
        db.refresh(place)
        upsert_place(place)
        if workspace_id:
            log_agent_event(
                db,
                workspace_id,
                "Researcher Agent",
                "Success",
                f"Geocoded {place.title}.",
                confidence=place.confidence,
                tools=["geocode_place"],
                input_preview=place.title,
                output_preview=f"{place.address or district}, lat={place.lat:.4f}",
                run_id=run_id,
            )
    return place


def _place_to_dict(place: PlaceModel) -> dict:
    return {
        "title": place.title,
        "city": place.city,
        "country": place.country,
        "category": place.category,
        "tags": place.tags,
        "description": place.description,
        "aestheticNote": place.aesthetic_note,
        "confidence": place.confidence,
        "address": place.address,
        "reason": place.reason,
    }


def _apply_enriched_fields(place: PlaceModel, enriched: dict) -> None:
    aesthetic = enriched.get("aestheticNote") or enriched.get("aesthetic_note")
    if enriched.get("description"):
        place.description = enriched["description"]
    if aesthetic:
        place.aesthetic_note = aesthetic
    if enriched.get("tags"):
        place.tags = normalize_aesthetic_tags(enriched["tags"], allow_custom=False)
    if enriched.get("category"):
        place.category = enriched["category"]
    if enriched.get("confidence"):
        place.confidence = float(enriched["confidence"])


async def enrich_place_with_gigachat(
    db: Session,
    place: PlaceModel,
    workspace_id: str,
    destination_hint: str = "",
    *,
    run_id: str | None = None,
) -> PlaceModel:
    run_id = run_id or new_run_id()
    tools: list[str] = ["gigachat_enrich"]
    place_dict = _place_to_dict(place)

    web_context = ""
    if tavily_service.available:
        query = f"{place.title} {place.city} {place.country}"
        results = tavily_service.search(query, max_results=3)
        if results:
            tools.append("tavily_search")
            web_context = "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:400]}"
                for r in results
            )

    enriched = await gigachat_service.enrich_place_card_with_web_async(
        place_dict,
        web_context,
        destination_hint,
    )
    _apply_enriched_fields(place, enriched)
    db.add(place)
    db.commit()
    db.refresh(place)

    log_agent_event(
        db,
        workspace_id,
        "Researcher Agent",
        "Success",
        f"GigaChat enriched {place.title}.",
        confidence=place.confidence,
        tools=tools,
        input_preview=place.title,
        output_preview=(place.description[:120] + "…") if len(place.description) > 120 else place.description,
        run_id=run_id,
    )

    return await enrich_place(db, place, workspace_id, run_id=run_id)


async def enrich_place(
    db: Session,
    place: PlaceModel,
    workspace_id: str,
    *,
    run_id: str | None = None,
) -> PlaceModel:
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
            run_id=run_id,
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
            run_id=run_id,
        )

    geocode_title = _geocode_title(place)
    lat, lng, district, resolved_address = await geocode_place(
        geocode_title,
        place.city,
        place.country,
        place.address or "",
        place.category,
    )
    if lat is not None and lng is not None:
        place.lat = lat
        place.lng = lng
        place.district = district
        if resolved_address and not place.address:
            place.address = resolved_address

    if tavily_service.available:
        if specific and verification == "Verified":
            # Tavily passed, but human review is still required before a Verified badge.
            place.verification = "Unverified"
            place.confidence = max(place.confidence, conf)
        else:
            place.verification = verification
            if not specific:
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
        output_preview=f"{place.verification}, address={place.address or place.district}",
        run_id=run_id,
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
