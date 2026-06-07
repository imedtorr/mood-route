import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.agents.curator import detect_source
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
from app.pipelines.ingest import run_ingest_pipeline
from app.rag.store import search_places, upsert_place, delete_place
from app.services.countries import country_to_flag, default_trip_name

from app.schemas import (
    ItineraryResponse,
    Place,
    PlaceSearchResult,
    PlaceUpdate,
    PreferencesUpdate,
    ReviewActionRequest,
    ReviewCard,
    TripGenerateRequest,
    Upload,
    UrlUploadRequest,
    Workspace,
    WorkspaceCreate,
)
from app.schemas.mappers import (
    agent_event_to_schema,
    itinerary_to_schema,
    place_to_schema,
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


PLACE_EDIT_FIELDS = {
    "title": "title",
    "city": "city",
    "country": "country",
    "category": "category",
    "description": "description",
    "aestheticNote": "aesthetic_note",
    "verification": "verification",
}


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
    return [workspace_to_schema(w) for w in db.query(WorkspaceModel).all()]


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
    return [place_to_schema(p) for p in q.all()]


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
            PlaceModel.title.ilike(f"%{q}%"),
        ).limit(12).all()
        return PlaceSearchResult(places=[place_to_schema(p) for p in places], query=q)
    id_order = {pid: i for i, pid in enumerate(place_ids)}
    places = db.query(PlaceModel).filter(PlaceModel.id.in_(place_ids)).all()
    places.sort(key=lambda p: id_order.get(p.id, 999))
    return PlaceSearchResult(places=[place_to_schema(p) for p in places], query=q)


@router.patch("/workspaces/{workspace_id}/places/{place_id}", response_model=Place)
def update_place(
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
    db.commit()
    db.refresh(place)
    upsert_place(place)
    return place_to_schema(place)


@router.delete("/workspaces/{workspace_id}/places/{place_id}")
def delete_place_endpoint(
    workspace_id: str,
    place_id: str,
    db: Session = Depends(get_db),
):
    get_workspace_or_404(db, workspace_id)
    place = get_place_or_404(db, workspace_id, place_id)
    place.status = "rejected"
    delete_place(workspace_id, place.id)
    db.add(place)
    db.commit()
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/uploads", response_model=list[Upload])
def list_uploads(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace_or_404(db, workspace_id)
    uploads = db.query(UploadModel).filter(UploadModel.workspace_id == workspace_id).order_by(
        UploadModel.created_at.desc()
    ).all()
    return [upload_to_schema(u) for u in uploads]


@router.get("/workspaces/{workspace_id}/uploads/{upload_id}", response_model=Upload)
def get_upload(workspace_id: str, upload_id: str, db: Session = Depends(get_db)):
    upload = db.query(UploadModel).filter(
        UploadModel.id == upload_id, UploadModel.workspace_id == workspace_id
    ).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload_to_schema(upload)


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
                place.status = "rejected"
                delete_place(workspace_id, place.id)
                db.add(place)
    elif body.action == "merge" and len(review.place_ids) >= 2:
        keep_id = body.mergeIntoPlaceId or review.place_ids[0]
        for pid in review.place_ids:
            if pid != keep_id:
                dup = db.get(PlaceModel, pid)
                if dup:
                    dup.status = "merged"
                    delete_place(workspace_id, dup.id)
                    db.add(dup)
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
        .order_by(AgentEventModel.created_at.asc())
        .limit(50)
        .all()
    )
    return [agent_event_to_schema(e) for e in events]
