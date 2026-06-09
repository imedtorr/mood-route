import uuid

from sqlalchemy.orm import Session

from app.agents.researcher import create_review_for_place
from app.db.models import PlaceModel, ReviewModel
from app.rag.embeddings import embed_text
from app.services.agent_log import log_agent_event
from app.services.tavily import tavily_service


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _is_likely_duplicate(p1: PlaceModel, p2: PlaceModel) -> bool:
    if p1.id == p2.id:
        return False
    if p1.city.lower().strip() != p2.city.lower().strip():
        return False
    t1, t2 = p1.title.lower().strip(), p2.title.lower().strip()
    if t1 == t2:
        return True
    if t1 in t2 or t2 in t1:
        return True
    return _cosine(embed_text(t1), embed_text(t2)) >= 0.88


def _duplicate_pairs(
    candidates: list[PlaceModel],
    against: list[PlaceModel],
) -> list[tuple[PlaceModel, PlaceModel]]:
    pairs: list[tuple[PlaceModel, PlaceModel]] = []
    seen: set[frozenset[str]] = set()
    for p1 in candidates:
        for p2 in against:
            if p1.id == p2.id:
                continue
            key = frozenset({p1.id, p2.id})
            if key in seen:
                continue
            if _is_likely_duplicate(p1, p2):
                pairs.append((p1, p2))
                seen.add(key)
    return pairs


async def verify_places(
    db: Session,
    workspace_id: str,
    places: list[PlaceModel],
    *,
    check_duplicates: bool = False,
    run_id: str | None = None,
) -> list[ReviewModel]:
    reviews: list[ReviewModel] = []
    merged = 0
    flagged = 0

    active = [p for p in places if p.status == "active"]
    if check_duplicates and active:
        existing = (
            db.query(PlaceModel)
            .filter(PlaceModel.workspace_id == workspace_id, PlaceModel.status == "active")
            .all()
        )
        for p1, p2 in _duplicate_pairs(active, existing):
            review = ReviewModel(
                id=f"r{uuid.uuid4().hex[:10]}",
                workspace_id=workspace_id,
                type="Duplicate place detected",
                title=f"{p1.title} vs {p2.title}",
                city=p1.city,
                country=p1.country,
                category=p1.category,
                confidence=0.92,
                explanation=(
                    f"Two extractions may refer to the same location in {p1.city}. "
                    "Consider merging to keep the knowledge base clean."
                ),
                source=p1.source,
                suggested_action="Merge Duplicate",
                image=p1.image,
                place_ids=[p1.id, p2.id],
                resolved=False,
            )
            db.add(review)
            reviews.append(review)
            merged += 1

    for place in active:
        if place.confidence < 0.7:
            reviews.append(
                create_review_for_place(
                    db,
                    workspace_id,
                    place,
                    "Low confidence extraction",
                    f"Extraction confidence is {place.confidence:.0%}. Please confirm or edit details.",
                    "Edit",
                )
            )
            flagged += 1
        elif place.verification == "Needs Recheck":
            reviews.append(
                create_review_for_place(
                    db,
                    workspace_id,
                    place,
                    "Possible closed/outdated place",
                    "Recommend manual recheck before adding to route.",
                    "Confirm",
                )
            )
            flagged += 1
        elif not tavily_service.available and place.verification == "Unverified":
            reviews.append(
                create_review_for_place(
                    db,
                    workspace_id,
                    place,
                    "Search unavailable — saved as draft",
                    "Verification tool was unavailable. Saved as Unverified draft.",
                    "Confirm",
                )
            )

    db.commit()

    status = "Needs Review" if reviews else "Success"
    log_agent_event(
        db,
        workspace_id,
        "Verifier Agent",
        status,
        f"Checked {len(active)} places — {merged} duplicate pairs, {flagged} flagged.",
        confidence=0.79 if reviews else 0.95,
        tools=["merge_duplicates", "verify_place_status"],
        input_preview=f"{len(active)} places",
        output_preview=f"{merged} duplicates, {flagged} flagged for review",
        run_id=run_id,
    )
    return reviews
