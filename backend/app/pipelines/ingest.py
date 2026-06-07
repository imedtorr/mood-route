import asyncio
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.curator import (
    detect_source,
    extract_place_from_screenshot,
    extract_place_from_text,
    fetch_url_content,
)
from app.agents.researcher import enrich_place
from app.agents.verifier import verify_places
from app.config import settings
from app.db.models import PlaceModel, UploadModel, WorkspaceModel
from app.rag.store import upsert_place
from app.services.agent_log import log_agent_event

STATUSES = [
    ("Parsing link", 15),
    ("OCR processing", 30),
    ("Extracting places", 50),
    ("Enriching details", 70),
    ("Classifying categories", 85),
    ("Awaiting review", 95),
    ("Completed", 100),
]


def _set_upload(db: Session, upload: UploadModel, status: str, progress: int) -> None:
    upload.status = status
    upload.progress = progress
    db.add(upload)
    db.commit()


async def run_ingest_pipeline(db: Session, upload_id: str) -> None:
    upload = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
    if not upload:
        return

    ws_id = upload.workspace_id
    workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == ws_id).first()
    destination_hint = workspace.destination if workspace else ""
    default_city, default_country = (
        (destination_hint.split(",")[0].strip(), destination_hint.split(",")[1].strip())
        if destination_hint and "," in destination_hint
        else (destination_hint, "")
    )
    log_agent_event(
        db,
        ws_id,
        "Supervisor Agent",
        "Success",
        f"Started ingest pipeline for upload {upload.title[:40]}.",
        tools=["delegate_task"],
        input_preview=upload_id,
        output_preview="Delegated to Curator → Researcher → Verifier.",
    )

    try:
        for status, progress in STATUSES[:-2]:
            _set_upload(db, upload, status, progress)
            await asyncio.sleep(0.3)

        raw_text = ""
        image = upload.image
        if upload.raw_url:
            title, text, og_image = await fetch_url_content(upload.raw_url)
            upload.title = title[:120] if title else upload.title
            raw_text = text
            if og_image:
                image = og_image
                upload.image = og_image
            _set_upload(db, upload, "Extracting places", 50)
            extracted = await extract_place_from_text(
                raw_text,
                upload.source,
                upload.note,
                image,
                destination_hint,
                page_title=upload.title,
            )
        elif upload.file_path and Path(upload.file_path).exists():
            _set_upload(db, upload, "OCR processing", 30)
            _set_upload(db, upload, "Extracting places", 50)
            extracted = await extract_place_from_screenshot(
                upload.file_path,
                upload.source,
                upload.note,
                image,
                destination_hint,
            )
        else:
            raw_text = upload.note or upload.title
            _set_upload(db, upload, "Extracting places", 50)
            extracted = await extract_place_from_text(
                raw_text,
                upload.source,
                upload.note,
                image,
                destination_hint,
                page_title=upload.title,
            )
        log_agent_event(
            db,
            ws_id,
            "Curator Agent",
            "Success" if extracted.get("confidence", 0) >= 0.7 else "Fallback",
            f"Extracted place: {extracted.get('title', 'Unknown')}.",
            confidence=float(extracted.get("confidence", 0.7)),
            tools=["vision_extract", "ocr_image", "extract_places"],
            input_preview=upload.title,
            output_preview=str(extracted.get("title")),
        )

        place = PlaceModel(
            id=f"p{uuid.uuid4().hex[:10]}",
            workspace_id=ws_id,
            title=extracted.get("title", "Discovered Place"),
            city=extracted.get("city", default_city or "Unknown"),
            country=extracted.get("country", default_country or "Unknown"),
            category=extracted.get("category", "Other"),
            source=upload.source,
            confidence=float(extracted.get("confidence", 0.7)),
            verification="Unverified",
            image=extracted.get("image") or image or upload.image,
            description=extracted.get("description", ""),
            aesthetic_note=extracted.get("aestheticNote", ""),
            reason=f"Extracted from {upload.source} inspiration.",
            upload_id=upload.id,
        )
        place.tags = extracted.get("tags", ["Hidden Gem"])
        db.add(place)
        db.commit()

        _set_upload(db, upload, "Enriching details", 70)
        place = await enrich_place(db, place, ws_id)

        _set_upload(db, upload, "Classifying categories", 85)
        await verify_places(db, ws_id, [place], check_duplicates=True)
        upsert_place(place)

        if place.confidence < 0.7 or place.verification in ("Unverified", "Needs Recheck"):
            _set_upload(db, upload, "Awaiting review", 95)
            upload.status = "Awaiting review"
        else:
            upload.status = "Completed"
        upload.progress = 100
        db.add(upload)
        db.commit()

    except Exception as exc:
        upload.status = "Fallback / Needs manual review"
        upload.progress = 100
        db.add(upload)
        db.commit()
        log_agent_event(
            db,
            ws_id,
            "Curator Agent",
            "Fallback",
            f"Pipeline failed: {exc}",
            confidence=0.4,
            tools=["extract_places"],
            input_preview=upload.title,
            output_preview="Needs manual review",
        )


def schedule_ingest(db: Session, upload_id: str) -> None:
    asyncio.create_task(run_ingest_pipeline(db, upload_id))
