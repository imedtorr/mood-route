import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.curator import (
    extract_place_from_query,
    extract_place_from_screenshot,
    extract_places_from_text,
    fetch_url_content,
)
from app.agents.researcher import enrich_place
from app.agents.verifier import verify_places
from app.db.models import PlaceModel, UploadModel, WorkspaceModel
from app.domain.places import is_place_specific
from app.rag.store import upsert_place
from app.services.agent_log import log_agent_event
from app.services.gigachat import gigachat_service


TERMINAL_UPLOAD_STATUSES = frozenset({
    "Completed",
    "Awaiting review",
    "Fallback / Needs manual review",
    "Cancelled",
})


def _is_cancelled(db: Session, upload_id: str) -> bool:
    upload = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
    return upload is None or upload.status == "Cancelled"


def _set_upload(db: Session, upload: UploadModel, status: str, progress: int) -> bool:
    db.refresh(upload)
    if upload.status == "Cancelled":
        return False
    upload.status = status
    upload.progress = progress
    db.add(upload)
    db.commit()
    return True


async def run_ingest_pipeline(db: Session, upload_id: str) -> None:
    upload = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
    if not upload or upload.status == "Cancelled":
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
        raw_text = ""
        image = upload.image
        extracted_list: list[dict] = []

        if upload.source == "Text":
            if not _set_upload(db, upload, "Extracting places", 50):
                return
            single = await extract_place_from_query(
                upload.title,
                upload.note,
                destination_hint,
            )
            extracted_list = [single] if single.get("title") else []
        elif upload.raw_url:
            if not _set_upload(db, upload, "Parsing link", 15):
                return
            title, text, og_image = await fetch_url_content(upload.raw_url)
            if _is_cancelled(db, upload_id):
                return
            upload.title = title[:120] if title else upload.title
            raw_text = text
            if og_image:
                image = og_image
                upload.image = og_image
            if not _set_upload(db, upload, "Extracting places", 50):
                return
            extracted_list = await extract_places_from_text(
                raw_text,
                upload.source,
                upload.note,
                image,
                destination_hint,
                page_title=upload.title,
            )
        elif upload.file_path and Path(upload.file_path).exists():
            if not _set_upload(db, upload, "OCR processing", 30):
                return
            single = await extract_place_from_screenshot(
                upload.file_path,
                upload.source,
                upload.note,
                image,
                destination_hint,
            )
            if _is_cancelled(db, upload_id):
                return
            if not _set_upload(db, upload, "Extracting places", 50):
                return
            extracted_list = [single] if single.get("title") else []
        else:
            raw_text = upload.note or upload.title
            if not _set_upload(db, upload, "Extracting places", 50):
                return
            extracted_list = await extract_places_from_text(
                raw_text,
                upload.source,
                upload.note,
                image,
                destination_hint,
                page_title=upload.title,
            )

        if not extracted_list:
            extracted_list = [{
                "title": "Discovered Place",
                "city": default_city or "Unknown",
                "country": default_country or "Unknown",
                "category": "Other",
                "tags": ["Hidden Gem"],
                "description": raw_text[:300] if raw_text else "",
                "aestheticNote": "A visually inspiring travel spot.",
                "confidence": 0.5,
                "image": image or upload.image,
            }]

        if gigachat_service.available:
            enriched: list[dict] = []
            for place in extracted_list:
                if _is_cancelled(db, upload_id):
                    return
                if is_place_specific(place):
                    enriched.append(
                        await gigachat_service.enrich_place_card_async(place, destination_hint)
                    )
                else:
                    enriched.append(place)
            extracted_list = enriched

        if _is_cancelled(db, upload_id):
            return

        place_titles = ", ".join(p.get("title", "Unknown") for p in extracted_list[:5])
        if len(extracted_list) > 5:
            place_titles += f" (+{len(extracted_list) - 5} more)"
        log_agent_event(
            db,
            ws_id,
            "Curator Agent",
            "Success" if all(p.get("confidence", 0) >= 0.7 for p in extracted_list) else "Fallback",
            f"Extracted {len(extracted_list)} place(s): {place_titles}.",
            confidence=float(sum(p.get("confidence", 0.7) for p in extracted_list) / len(extracted_list)),
            tools=["ollama_vision", "ollama_text", "extract_places"],
            input_preview=upload.title,
            output_preview=place_titles,
        )

        places: list[PlaceModel] = []
        for extracted in extracted_list:
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
            places.append(place)
        db.commit()

        if not _set_upload(db, upload, "Enriching details", 70):
            return
        for idx, place in enumerate(places):
            if _is_cancelled(db, upload_id):
                return
            places[idx] = await enrich_place(db, place, ws_id)

        if not _set_upload(db, upload, "Classifying categories", 85):
            return
        await verify_places(db, ws_id, places, check_duplicates=True)
        for place in places:
            upsert_place(place)

        if _is_cancelled(db, upload_id):
            return

        needs_review = any(
            p.confidence < 0.7 or p.verification in ("Unverified", "Needs Recheck")
            for p in places
        )
        if needs_review:
            upload.status = "Awaiting review"
            upload.progress = 95
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
