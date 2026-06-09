from sqlalchemy.orm import Session

from app.db.models import PlaceModel, ReviewModel, UploadModel


def resolve_reviews_for_place(db: Session, workspace_id: str, place_id: str) -> None:
    reviews = db.query(ReviewModel).filter(
        ReviewModel.workspace_id == workspace_id,
        ReviewModel.resolved == False,
    ).all()
    for review in reviews:
        if place_id in review.place_ids:
            review.resolved = True
            db.add(review)


def upload_ids_for_places(db: Session, workspace_id: str, place_ids: list[str]) -> set[str]:
    if not place_ids:
        return set()
    rows = (
        db.query(PlaceModel.upload_id)
        .filter(
            PlaceModel.workspace_id == workspace_id,
            PlaceModel.id.in_(place_ids),
            PlaceModel.upload_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return {uid for (uid,) in rows if uid}


def try_complete_upload_review(db: Session, workspace_id: str, upload_id: str) -> bool:
    upload = db.query(UploadModel).filter(
        UploadModel.id == upload_id,
        UploadModel.workspace_id == workspace_id,
    ).first()
    if not upload or upload.status != "Awaiting review":
        return False

    place_ids = [
        pid
        for (pid,) in db.query(PlaceModel.id)
        .filter(
            PlaceModel.workspace_id == workspace_id,
            PlaceModel.upload_id == upload_id,
            PlaceModel.status == "active",
        )
        .all()
    ]

    unresolved = db.query(ReviewModel).filter(
        ReviewModel.workspace_id == workspace_id,
        ReviewModel.resolved == False,
    ).all()
    for review in unresolved:
        if any(pid in review.place_ids for pid in place_ids):
            return False

    if place_ids:
        unverified = (
            db.query(PlaceModel)
            .filter(
                PlaceModel.workspace_id == workspace_id,
                PlaceModel.upload_id == upload_id,
                PlaceModel.status == "active",
                PlaceModel.verification != "Verified",
            )
            .first()
        )
        if unverified:
            return False

    upload.status = "Completed"
    upload.progress = 100
    db.add(upload)
    return True


def try_complete_uploads_for_places(db: Session, workspace_id: str, place_ids: list[str]) -> None:
    for upload_id in upload_ids_for_places(db, workspace_id, place_ids):
        try_complete_upload_review(db, workspace_id, upload_id)
