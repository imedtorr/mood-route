from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AgentEventModel,
    ItineraryModel,
    PlaceModel,
    ReviewModel,
    UploadModel,
    WorkspaceModel,
)
from app.rag.store import delete_workspace_collection


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def touch_workspace(db: Session, workspace_id: str) -> None:
    ws = db.get(WorkspaceModel, workspace_id)
    if ws:
        ws.updated_at = utcnow()
        db.add(ws)


def _remove_upload_file(upload: UploadModel) -> None:
    if upload.file_path:
        path = Path(upload.file_path)
        if path.exists():
            path.unlink(missing_ok=True)


def delete_workspace(db: Session, workspace_id: str) -> None:
    from app.pipelines.ingest import TERMINAL_UPLOAD_STATUSES

    ws = db.get(WorkspaceModel, workspace_id)
    if not ws:
        return

    uploads = db.query(UploadModel).filter(UploadModel.workspace_id == workspace_id).all()
    for upload in uploads:
        if upload.status not in TERMINAL_UPLOAD_STATUSES:
            upload.status = "Cancelled"
            db.add(upload)
    db.flush()

    for upload in uploads:
        _remove_upload_file(upload)

    delete_workspace_collection(workspace_id)

    db.query(PlaceModel).filter(PlaceModel.workspace_id == workspace_id).delete()
    db.query(UploadModel).filter(UploadModel.workspace_id == workspace_id).delete()
    db.query(ReviewModel).filter(ReviewModel.workspace_id == workspace_id).delete()
    db.query(AgentEventModel).filter(AgentEventModel.workspace_id == workspace_id).delete()
    db.query(ItineraryModel).filter(ItineraryModel.workspace_id == workspace_id).delete()
    db.delete(ws)
    db.commit()


def backfill_workspace_updated_at(db: Session) -> None:
    for ws in db.query(WorkspaceModel).all():
        latest_upload = (
            db.query(func.max(UploadModel.created_at))
            .filter(UploadModel.workspace_id == ws.id)
            .scalar()
        )
        latest_event = (
            db.query(func.max(AgentEventModel.created_at))
            .filter(AgentEventModel.workspace_id == ws.id)
            .scalar()
        )
        latest_trip = (
            db.query(func.max(ItineraryModel.created_at))
            .filter(ItineraryModel.workspace_id == ws.id)
            .scalar()
        )
        candidates = [t for t in (latest_upload, latest_event, latest_trip) if t is not None]
        ws.updated_at = max(candidates) if candidates else utcnow()
        db.add(ws)
    db.commit()
