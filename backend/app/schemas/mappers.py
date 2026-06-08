import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import (
    AgentEventModel,
    ItineraryModel,
    PlaceModel,
    ReviewModel,
    UploadModel,
    WorkspaceModel,
)
from app.services.countries import parse_destination

from app.schemas import (
    AgentTimelineEntry,
    ItineraryDay,
    ItineraryResponse,
    ItineraryStop,
    Place,
    ReviewCard,
    SourcesSummary,
    Upload,
    Workspace,
)


def _relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return "yesterday"


def workspace_to_schema(w: WorkspaceModel) -> Workspace:
    city = w.city or ""
    country = w.country or ""
    if not city or not country:
        parsed_city, parsed_country = parse_destination(w.destination)
        city = city or parsed_city
        country = country or parsed_country
    updated = w.updated_at.isoformat() if w.updated_at else None
    return Workspace(
        id=w.id,
        name=w.name,
        flag=w.flag,
        country=country,
        city=city,
        destination=w.destination or (f"{city}, {country}" if city and country else ""),
        updatedAt=updated,
    )


def _source_urls_for_places(db: Session, places: list[PlaceModel]) -> dict[str, str]:
    upload_ids = {p.upload_id for p in places if p.upload_id}
    if not upload_ids:
        return {}
    rows = (
        db.query(UploadModel.id, UploadModel.raw_url)
        .filter(UploadModel.id.in_(upload_ids))
        .all()
    )
    return {uid: url for uid, url in rows if url}


def place_to_schema(p: PlaceModel, source_url: str | None = None) -> Place:
    return Place(
        id=p.id,
        title=p.title,
        city=p.city,
        country=p.country,
        category=p.category,
        tags=p.tags,
        source=p.source,
        confidence=p.confidence,
        verification=p.verification,
        image=p.image,
        description=p.description,
        aestheticNote=p.aesthetic_note,
        reason=p.reason,
        height=p.height,
        lat=p.lat,
        lng=p.lng,
        district=p.district,
        address=p.address or "",
        sourceUrl=source_url,
    )


def places_to_schema(db: Session, places: list[PlaceModel]) -> list[Place]:
    url_by_upload = _source_urls_for_places(db, places)
    return [
        place_to_schema(p, url_by_upload.get(p.upload_id) if p.upload_id else None)
        for p in places
    ]


def upload_to_schema(u: UploadModel, place_ids: list[str] | None = None) -> Upload:
    return Upload(
        id=u.id,
        title=u.title,
        source=u.source,
        time=_relative_time(u.created_at),
        status=u.status,
        progress=u.progress,
        image=u.image,
        note=u.note or "",
        placeIds=place_ids or [],
    )


def agent_event_to_schema(e: AgentEventModel) -> AgentTimelineEntry:
    return AgentTimelineEntry(
        id=e.id,
        agent=e.agent,
        time=_relative_time(e.created_at),
        status=e.status,
        summary=e.summary,
        confidence=e.confidence,
        tools=e.tools,
        input=e.input_preview,
        output=e.output_preview,
    )


def review_to_schema(r: ReviewModel) -> ReviewCard:
    return ReviewCard(
        id=r.id,
        type=r.type,
        title=r.title,
        city=r.city,
        country=r.country,
        category=r.category,
        confidence=r.confidence,
        explanation=r.explanation,
        source=r.source,
        suggestedAction=r.suggested_action,
        image=r.image,
        placeIds=r.place_ids,
    )


def itinerary_to_schema(it: ItineraryModel) -> ItineraryResponse:
    days_data = json.loads(it.days_json)
    days = [ItineraryDay(**d) for d in days_data]
    summary_raw = json.loads(it.sources_summary_json or "{}")
    return ItineraryResponse(
        days=days,
        sourcesSummary=SourcesSummary(**summary_raw),
        routeSummary=it.route_summary,
        tripRequest=json.loads(it.trip_request_json or "{}"),
    )
