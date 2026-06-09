"""One-off script to normalize aesthetic tags on existing places.

Usage (from backend/):
    python -m scripts.normalize_place_tags
"""

from app.db.database import SessionLocal, init_db
from app.db.models import PlaceModel
from app.services.llm_utils import AESTHETIC_TAGS, _resolve_aesthetic_tag, normalize_aesthetic_tags

CANONICAL_SET = set(AESTHETIC_TAGS)


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        places = db.query(PlaceModel).all()
        alias_mapped = 0
        custom_kept = 0
        updated = 0

        for place in places:
            original = place.tags
            normalized = normalize_aesthetic_tags(original, allow_custom=True)

            for tag in original:
                if tag in CANONICAL_SET:
                    continue
                if _resolve_aesthetic_tag(tag):
                    alias_mapped += 1
                elif tag in normalized:
                    custom_kept += 1

            if normalized != original:
                place.tags = normalized
                updated += 1

        db.commit()
        print(f"Places scanned: {len(places)}")
        print(f"Places updated: {updated}")
        print(f"Alias mappings applied: {alias_mapped}")
        print(f"Custom tags preserved: {custom_kept}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
