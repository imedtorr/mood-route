import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.agents.curator import detect_source, is_blocked_social_url
from app.agents.graph import run_trip_generation
from app.config import settings
from app.db.database import SessionLocal, get_db
from app.db.models import (
    AgentEventModel,
    ItineraryModel,
    PlaceModel,
    ReviewModel,
    UploadModel,
    WorkspaceModel,
)
from app.agents.researcher import ensure_place_geocoded
from app.pipelines.ingest import TERMINAL_UPLOAD_STATUSES, run_ingest_pipeline
from app.rag.store import search_places, upsert_place, delete_place
from app.services.countries import country_to_flag, default_trip_name
from app.services.workspaces import delete_workspace, touch_workspace

from app.schemas import (
    ItineraryResponse,
    Place,
    PlaceSearchResult,
    PlaceUpdate,
    PreferencesUpdate,
    ReviewActionRequest,
    ReviewCard,
    TextUploadRequest,
    TripGenerateRequest,
    Upload,
    UrlUploadRequest,
    Workspace,
    WorkspaceCreate,
)
from app.schemas.mappers import (
    agent_event_to_schema,
    itinerary_to_schema,
    places_to_schema,
    review_to_schema,
    upload_to_schema,
    workspace_to_schema,
)

router = APIRouter(prefix="/api")


def get_workspace_or_404(db: Session, workspace_id: str) -> WorkspaceModel:
    ws = db.get(WorkspaceModel, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


def get_place_or_404(db: Session, workspace_id: str, place_id: str) -> PlaceModel:
    place = db.query(PlaceModel).filter(
        PlaceModel.id == place_id,
        PlaceModel.workspace_id == workspace_id,
        PlaceModel.status == "active",
    ).first()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


def permanently_remove_place(db: Session, workspace_id: str, place: PlaceModel) -> None:
    delete_place(workspace_id, place.id)
    reviews = db.query(ReviewModel).filter(
        ReviewModel.workspace_id == workspace_id,
        ReviewModel.resolved == False,
    ).all()
    for review in reviews:
        if place.id in review.place_ids:
            review.resolved = True
            db.add(review)
    db.delete(place)


PLACE_EDIT_FIELDS = {
    "title": "title",
    "city": "city",
    "country": "country",
    "category": "category",
    "description": "description",
    "aestheticNote": "aesthetic_note",
    "verification": "verification",
    "address": "address",
}

GEOCODE_TRIGGER_FIELDS = frozenset({"title", "city", "country", "address"})


def apply_place_edits(place: PlaceModel, edits: dict) -> None:
    for key, val in edits.items():
        if key == "tags" and isinstance(val, list):
            place.tags = val
            continue
        attr = PLACE_EDIT_FIELDS.get(key)
        if attr and val is not None:
            setattr(place, attr, val)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/workspaces", response_model=list[Workspace])
def list_workspaces(db: Session = Depends(get_db)):
    rows = (
        db.query(WorkspaceModel)
        .order_by(WorkspaceModel.updated_at.desc())
        .all()
    )
    return [workspace_to_schema(w) for w in rows]


@router.post("/workspaces", response_model=Workspace)
def create_workspace(body: WorkspaceCreate, db: Session = Depends(get_db)):
    country = body.country.strip()
    city = body.city.strip()
    if not country or not city:
        raise HTTPException(status_code=400, detail="Country and city are required")

    name = body.name.strip() if body.name and body.name.strip() else default_trip_name(country)
    flag = body.flag.strip() if body.flag else country_to_flag(country)
    destination = f"{city}, {country}"

    ws = WorkspaceModel(
        id=f"ws{uuid.uuid4().hex[:10]}",
        name=name,
        flag=flag,
        country=country,
        city=city,
        destination=destination,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return workspace_to_schema(ws)


@router.delete("/workspaces/{workspace_id}")
def delete_workspace_endpoint(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace_or_404(db, workspace_id)
    delete_workspace(db, workspace_id)
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/places", response_model=list[Place])
def list_places(
    workspace_id: str,
    city: str | None = None,
    category: str | None = None,
    verification: str | None = None,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    q = db.query(PlaceModel).filter(
        PlaceModel.workspace_id == workspace_id,
        PlaceModel.status == "active",
    )
    if city and city != "All":
        q = q.filter(PlaceModel.city == city)
    if category and category != "All":
        q = q.filter(PlaceModel.category == category)
    if verification and verification != "All":
        q = q.filter(PlaceModel.verification == verification)
    return places_to_schema(db, q.all())


@router.get("/workspaces/{workspace_id}/places/search", response_model=PlaceSearchResult)
def search_places_endpoint(
    workspace_id: str,
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    results = search_places(workspace_id, q, n=12)
    place_ids = [pid for pid, _ in results]
    if not place_ids:
        places = db.query(PlaceModel).filter(
            PlaceModel.workspace_id == workspace_id,
            PlaceModel.status == "active",
            PlaceModel.title.ilike(f"%{q}%"),
        ).limit(12).all()
        return PlaceSearchResult(places=places_to_schema(db, places), query=q)
    id_order = {pid: i for i, pid in enumerate(place_ids)}
    places = db.query(PlaceModel).filter(
        PlaceModel.id.in_(place_ids),
        PlaceModel.status == "active",
    ).all()
    places.sort(key=lambda p: id_order.get(p.id, 999))
    return PlaceSearchResult(places=places_to_schema(db, places), query=q)


@router.patch("/workspaces/{workspace_id}/places/{place_id}", response_model=Place)
async def update_place(
    workspace_id: str,
    place_id: str,
    body: PlaceUpdate,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    place = get_place_or_404(db, workspace_id, place_id)
    edits = body.model_dump(exclude_unset=True)
    apply_place_edits(place, edits)
    db.add(place)
    touch_workspace(db, workspace_id)
    db.commit()
    db.refresh(place)
    if GEOCODE_TRIGGER_FIELDS & set(edits.keys()):
        await ensure_place_geocoded(db, place, workspace_id, force=True)
    else:
        upsert_place(place)
    db.refresh(place)
    return places_to_schema(db, [place])[0]


@router.post("/workspaces/{workspace_id}/places/{place_id}/geocode", response_model=Place)
async def geocode_place_endpoint(
    workspace_id: str,
    place_id: str,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    place = get_place_or_404(db, workspace_id, place_id)
    await ensure_place_geocoded(db, place, workspace_id, force=True)
    touch_workspace(db, workspace_id)
    db.refresh(place)
    return places_to_schema(db, [place])[0]


@router.delete("/workspaces/{workspace_id}/places/{place_id}")
def delete_place_endpoint(
    workspace_id: str,
    place_id: str,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    place = get_place_or_404(db, workspace_id, place_id)
    permanently_remove_place(db, workspace_id, place)
    touch_workspace(db, workspace_id)
    db.commit()
    return {"ok": True}


def _place_ids_by_upload(db: Session, workspace_id: str, upload_ids: list[str]) -> dict[str, list[str]]:
    if not upload_ids:
        return {}
    rows = (
        db.query(PlaceModel.upload_id, PlaceModel.id)
        .filter(
            PlaceModel.workspace_id == workspace_id,
            PlaceModel.upload_id.in_(upload_ids),
            PlaceModel.status == "active",
        )
        .all()
    )
    grouped: dict[str, list[str]] = {}
    for upload_id, place_id in rows:
        if upload_id:
            grouped.setdefault(upload_id, []).append(place_id)
    return grouped


def get_upload_or_404(db: Session, workspace_id: str, upload_id: str) -> UploadModel:
    upload = db.query(UploadModel).filter(
        UploadModel.id == upload_id,
        UploadModel.workspace_id == workspace_id,
    ).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


def _remove_upload_file(upload: UploadModel) -> None:
    if upload.file_path:
        path = Path(upload.file_path)
        if path.exists():
            path.unlink(missing_ok=True)


@router.get("/workspaces/{workspace_id}/uploads", response_model=list[Upload])
def list_uploads(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace_or_404(db, workspace_id)
    uploads = db.query(UploadModel).filter(UploadModel.workspace_id == workspace_id).order_by(
        UploadModel.created_at.desc()
    ).all()
    place_ids_map = _place_ids_by_upload(db, workspace_id, [u.id for u in uploads])
    return [upload_to_schema(u, place_ids_map.get(u.id, [])) for u in uploads]


@router.get("/workspaces/{workspace_id}/uploads/{upload_id}", response_model=Upload)
def get_upload(workspace_id: str, upload_id: str, db: Session = Depends(get_db)):
    upload = get_upload_or_404(db, workspace_id, upload_id)
    place_ids = _place_ids_by_upload(db, workspace_id, [upload.id]).get(upload.id, [])
    return upload_to_schema(upload, place_ids)


@router.post("/workspaces/{workspace_id}/uploads/{upload_id}/cancel", response_model=Upload)
def cancel_upload(workspace_id: str, upload_id: str, db: Session = Depends(get_db)):
    upload = get_upload_or_404(db, workspace_id, upload_id)
    if upload.status in TERMINAL_UPLOAD_STATUSES:
        raise HTTPException(status_code=400, detail="Upload is not running")
    upload.status = "Cancelled"
    upload.progress = 100
    db.add(upload)
    touch_workspace(db, workspace_id)
    db.commit()
    db.refresh(upload)
    return upload_to_schema(upload)


@router.delete("/workspaces/{workspace_id}/uploads/{upload_id}")
def delete_upload(workspace_id: str, upload_id: str, db: Session = Depends(get_db)):
    upload = get_upload_or_404(db, workspace_id, upload_id)
    if upload.status not in TERMINAL_UPLOAD_STATUSES:
        upload.status = "Cancelled"
        db.add(upload)
        db.commit()
    _remove_upload_file(upload)
    db.delete(upload)
    touch_workspace(db, workspace_id)
    db.commit()
    return {"ok": True}


def _run_ingest_task(upload_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(run_ingest_pipeline(db, upload_id))
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/uploads/url", response_model=Upload)
def create_url_upload(
    workspace_id: str,
    body: UrlUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    if is_blocked_social_url(body.url):
        raise HTTPException(
            status_code=400,
            detail="Only article links are supported. For social media posts, upload a screenshot instead.",
        )
    upload = UploadModel(
        id=f"u{uuid.uuid4().hex[:10]}",
        workspace_id=workspace_id,
        title=body.url.replace("https://", "").replace("http://", "")[:80],
        source=detect_source(body.url),
        status="Parsing link",
        progress=8,
        image="https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=400&h=400&q=80",
        note=body.note,
        raw_url=body.url,
    )
    db.add(upload)
    touch_workspace(db, workspace_id)
    db.commit()
    db.refresh(upload)
    background_tasks.add_task(_run_ingest_task, upload.id)
    return upload_to_schema(upload)


@router.post("/workspaces/{workspace_id}/uploads/text", response_model=Upload)
def create_text_upload(
    workspace_id: str,
    body: TextUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    upload = UploadModel(
        id=f"u{uuid.uuid4().hex[:10]}",
        workspace_id=workspace_id,
        title=body.query.strip()[:120],
        source="Text",
        status="Extracting places",
        progress=8,
        image="https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=400&h=400&q=80",
        note=body.note,
    )
    db.add(upload)
    touch_workspace(db, workspace_id)
    db.commit()
    db.refresh(upload)
    background_tasks.add_task(_run_ingest_task, upload.id)
    return upload_to_schema(upload)


@router.post("/workspaces/{workspace_id}/uploads/file", response_model=Upload)
async def create_file_upload(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    note: str = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_id = f"u{uuid.uuid4().hex[:10]}"
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    file_path = upload_dir / f"{upload_id}{ext}"
    content = await file.read()
    file_path.write_bytes(content)

    upload = UploadModel(
        id=upload_id,
        workspace_id=workspace_id,
        title=file.filename or "Screenshot upload",
        source="Screenshot",
        status="Parsing link",
        progress=8,
        image=f"/api/uploads/{upload_id}{ext}",
        note=note,
        file_path=str(file_path),
    )
    db.add(upload)
    touch_workspace(db, workspace_id)
    db.commit()
    db.refresh(upload)
    background_tasks.add_task(_run_ingest_task, upload.id)
    return upload_to_schema(upload)


@router.get("/workspaces/{workspace_id}/review", response_model=list[ReviewCard])
def list_reviews(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace_or_404(db, workspace_id)
    reviews = db.query(ReviewModel).filter(
        ReviewModel.workspace_id == workspace_id,
        ReviewModel.resolved == False,
    ).all()
    return [review_to_schema(r) for r in reviews]


@router.post("/workspaces/{workspace_id}/review/{review_id}/action")
def review_action(
    workspace_id: str,
    review_id: str,
    body: ReviewActionRequest,
    db: Session = Depends(get_db),
):
    review = db.query(ReviewModel).filter(
        ReviewModel.id == review_id, ReviewModel.workspace_id == workspace_id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review item not found")

    if body.action == "confirm":
        if review.place_ids:
            place = db.get(PlaceModel, review.place_ids[0])
            if place:
                place.verification = "Verified"
                place.confidence = max(place.confidence, 0.85)
                db.add(place)
                upsert_place(place)
    elif body.action == "reject":
        if review.place_ids:
            place = db.get(PlaceModel, review.place_ids[0])
            if place:
                permanently_remove_place(db, workspace_id, place)
    elif body.action == "merge" and len(review.place_ids) >= 2:
        keep_id = body.mergeIntoPlaceId or review.place_ids[0]
        for pid in review.place_ids:
            if pid != keep_id:
                dup = db.get(PlaceModel, pid)
                if dup:
                    permanently_remove_place(db, workspace_id, dup)
        keep = db.get(PlaceModel, keep_id)
        if keep:
            keep.verification = "Verified"
            db.add(keep)
            upsert_place(keep)
    elif body.action == "edit" and body.edits:
        pid = review.place_ids[0] if review.place_ids else None
        if pid:
            place = db.get(PlaceModel, pid)
            if place:
                apply_place_edits(place, body.edits)
                place.confidence = max(place.confidence, 0.8)
                place.verification = "Verified"
                db.add(place)
                upsert_place(place)

    review.resolved = True
    db.add(review)
    touch_workspace(db, workspace_id)
    db.commit()
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/preferences")
def get_preferences(workspace_id: str, db: Session = Depends(get_db)):
    ws = get_workspace_or_404(db, workspace_id)
    return {"preferences": ws.preferences}


@router.patch("/workspaces/{workspace_id}/preferences")
def update_preferences(workspace_id: str, body: PreferencesUpdate, db: Session = Depends(get_db)):
    ws = get_workspace_or_404(db, workspace_id)
    ws.preferences = body.preferences
    db.add(ws)
    touch_workspace(db, workspace_id)
    db.commit()
    return {"preferences": ws.preferences}


@router.post("/workspaces/{workspace_id}/trips/generate", response_model=ItineraryResponse)
async def generate_trip(
    workspace_id: str,
    body: TripGenerateRequest,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    places = db.query(PlaceModel).filter(
        PlaceModel.workspace_id == workspace_id,
        PlaceModel.status == "active",
    ).all()
    if not places:
        raise HTTPException(status_code=400, detail="No places in workspace")

    days, sources, summary = await run_trip_generation(db, workspace_id, places, body)

    db.query(ItineraryModel).filter(
        ItineraryModel.workspace_id == workspace_id,
        ItineraryModel.is_latest == True,
    ).update({"is_latest": False})

    it = ItineraryModel(
        id=f"it{uuid.uuid4().hex[:10]}",
        workspace_id=workspace_id,
        days_json=json.dumps([d.model_dump() for d in days], ensure_ascii=False),
        sources_summary_json=json.dumps(sources.model_dump()),
        route_summary=summary,
        trip_request_json=json.dumps(body.model_dump()),
        is_latest=True,
    )
    db.add(it)
    touch_workspace(db, workspace_id)
    db.commit()

    return itinerary_to_schema(it)


@router.get("/workspaces/{workspace_id}/trips/latest", response_model=ItineraryResponse)
def latest_trip(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace_or_404(db, workspace_id)
    it = db.query(ItineraryModel).filter(
        ItineraryModel.workspace_id == workspace_id,
        ItineraryModel.is_latest == True,
    ).order_by(ItineraryModel.created_at.desc()).first()
    if not it:
        raise HTTPException(status_code=404, detail="No itinerary yet")
    return itinerary_to_schema(it)


@router.get("/workspaces/{workspace_id}/agent-events")
def list_agent_events(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace_or_404(db, workspace_id)
    events = (
        db.query(AgentEventModel)
        .filter(AgentEventModel.workspace_id == workspace_id)
        .order_by(AgentEventModel.created_at.desc())
        .limit(50)
        .all()
    )
    return [agent_event_to_schema(e) for e in events]
