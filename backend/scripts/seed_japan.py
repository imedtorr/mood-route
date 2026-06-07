import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.database import SessionLocal, init_db
from app.db.models import (
    AgentEventModel,
    ItineraryModel,
    PlaceModel,
    ReviewModel,
    UploadModel,
    WorkspaceModel,
)
from app.rag.store import bulk_upsert_places

IMG = lambda pid, w=600, h=800: (
    f"https://images.unsplash.com/photo-{pid}?auto=format&fit=crop&w={w}&h={h}&q=80"
)

PLACES = [
    {"id": "p1", "title": "Hidden Coffee Roastery", "city": "Tokyo", "country": "Japan", "category": "Cafe",
     "tags": ["Minimal", "Coffee Culture", "Slow Travel"], "source": "Screenshot", "confidence": 0.94,
     "verification": "Verified", "image": IMG("1495474472287-4d71bcdd2085"), "district": "Nakameguro",
     "lat": 35.6442, "lng": 139.6982,
     "description": "Quiet third-wave roastery tucked in a Nakameguro alley.",
     "aesthetic_note": "Quiet minimalist café perfect for a slow morning.",
     "reason": "Matches your Coffee Culture and Minimal preferences.", "height": 320},
    {"id": "p2", "title": "teamLab Planets", "city": "Tokyo", "country": "Japan", "category": "Museum",
     "tags": ["Neon", "Photography", "Creative"], "source": "Text", "confidence": 0.97,
     "verification": "Verified", "image": IMG("1480796927426-f609979314bd", 600, 700), "district": "Toyosu",
     "lat": 35.6493, "lng": 139.7896,
     "description": "Immersive digital art museum in Toyosu.",
     "aesthetic_note": "Otherworldly light environments — book the evening slot.",
     "reason": "You pinned 3 immersive art spaces this week.", "height": 280},
    {"id": "p3", "title": "Yanaka Ginza", "city": "Tokyo", "country": "Japan", "category": "Neighborhood",
     "tags": ["Vintage", "Hidden Gem", "Slow Travel"], "source": "Article", "confidence": 0.88,
     "verification": "Verified", "image": IMG("1528360983277-13d401cdc186"), "district": "Yanaka",
     "lat": 35.7266, "lng": 139.7677,
     "description": "Old Shitamachi shopping street with senbei shops.",
     "aesthetic_note": "Golden-hour light, terracotta rooftops, slow stroll.",
     "reason": "Walkable and matches your Hidden Gems mood.", "height": 340},
    {"id": "p4", "title": "Aoyama Flower Market Tea House", "city": "Tokyo", "country": "Japan", "category": "Cafe",
     "tags": ["Cozy", "Photography"], "source": "Text", "confidence": 0.91,
     "verification": "Verified", "image": IMG("1554118811-1e0d58224f24", 600, 700), "district": "Omotesando",
     "lat": 35.6654, "lng": 139.7126,
     "description": "Greenhouse café surrounded by florist arrangements.",
     "aesthetic_note": "A botanical pocket inside the city.",
     "reason": "Adds visual variety to your café crawl.", "height": 260},
    {"id": "p5", "title": "Nezu Museum Garden", "city": "Tokyo", "country": "Japan", "category": "Park",
     "tags": ["Architecture", "Slow Travel"], "source": "Text", "confidence": 0.93,
     "verification": "Verified", "image": IMG("1545569341-9eb8b30979d9"), "district": "Aoyama",
     "lat": 35.6617, "lng": 139.7175,
     "description": "Kuma Kengo-designed museum with a strolling garden.",
     "aesthetic_note": "Mossy quiet — best on a weekday morning.",
     "reason": "You bookmarked 2 Kuma projects.", "height": 330},
    {"id": "p6", "title": "Daikanyama T-Site", "city": "Tokyo", "country": "Japan", "category": "Shopping",
     "tags": ["Architecture", "Minimal"], "source": "Screenshot", "confidence": 0.9,
     "verification": "Verified", "image": IMG("1542051841857-5f90071e7989", 600, 700), "district": "Daikanyama",
     "lat": 35.6485, "lng": 139.7031,
     "description": "Tsutaya bookstore complex with woven-facade architecture.",
     "aesthetic_note": "Lattice shadows across the courtyard at dusk.",
     "reason": "Pairs with nearby cafés on your saved list.", "height": 280},
    {"id": "p7", "title": "Omoide Yokocho", "city": "Tokyo", "country": "Japan", "category": "Restaurant",
     "tags": ["Neon", "Vintage"], "source": "Screenshot", "confidence": 0.82,
     "verification": "Needs Recheck", "image": IMG("1554797589-7241bb691973"), "district": "Shinjuku",
     "lat": 35.6938, "lng": 139.6994,
     "description": "Postwar alley of tiny yakitori counters.",
     "aesthetic_note": "Smoke, neon, and shoulder-to-shoulder seats.",
     "reason": "Anchor for your neon evening route.", "height": 320},
    {"id": "p8", "title": "Shibuya Sky", "city": "Tokyo", "country": "Japan", "category": "Viewpoint",
     "tags": ["Photography"], "source": "Text", "confidence": 0.95,
     "verification": "Verified", "image": IMG("1540959733332-eab4deabeeaf", 600, 700), "district": "Shibuya",
     "lat": 35.6586, "lng": 139.7016,
     "description": "Open-air rooftop observatory above Shibuya scramble.",
     "aesthetic_note": "Golden hour onto blue hour, all in one window.",
     "reason": "Your saved viewpoints favor sunset slots.", "height": 280},
    {"id": "p9", "title": "Onibus Coffee Nakameguro", "city": "Tokyo", "country": "Japan", "category": "Cafe",
     "tags": ["Coffee Culture", "Minimal"], "source": "Screenshot", "confidence": 0.86,
     "verification": "Unverified", "image": IMG("1453614512568-c4024d13c247"), "district": "Nakameguro",
     "lat": 35.6338, "lng": 139.6989,
     "description": "Two-floor specialty café beside the train tracks.",
     "aesthetic_note": "Trains pass like a slow metronome.",
     "reason": "Top match for your Coffee Crawl style.", "height": 340},
    {"id": "p10", "title": "Meiji Jingu Forest Path", "city": "Tokyo", "country": "Japan", "category": "Park",
     "tags": ["Slow Travel", "Hidden Gem"], "source": "Article", "confidence": 0.92,
     "verification": "Verified", "image": IMG("1528164344705-47542687000d", 600, 700), "district": "Harajuku",
     "lat": 35.6764, "lng": 139.6993,
     "description": "Hand-planted urban forest leading to the Meiji shrine.",
     "aesthetic_note": "Cathedral hush, dappled light.",
     "reason": "Balances dense days with green space.", "height": 280},
    {"id": "p11", "title": "Higashiya Ginza", "city": "Tokyo", "country": "Japan", "category": "Cafe",
     "tags": ["Minimal", "Slow Travel"], "source": "Text", "confidence": 0.89,
     "verification": "Verified", "image": IMG("1517248135467-4c7edcad34c4"), "district": "Ginza",
     "lat": 35.6717, "lng": 139.7650,
     "description": "Modern wagashi salon with seasonal sweets.",
     "aesthetic_note": "Cedar, paper, single chrysanthemum.",
     "reason": "Quiet afternoon stop on your Ginza day.", "height": 320},
    {"id": "p12", "title": "Tsukiji Outer Market", "city": "Tokyo", "country": "Japan", "category": "Market",
     "tags": ["Photography", "Hidden Gem"], "source": "Article", "confidence": 0.84,
     "verification": "Needs Recheck", "image": IMG("1583224964978-2257b960c3d3", 600, 700), "district": "Tsukiji",
     "lat": 35.6654, "lng": 139.7707,
     "description": "Early-morning food stalls and knife shops.",
     "aesthetic_note": "Steam, shouts, neat rows of fish.",
     "reason": "Anchors a market morning route.", "height": 280},
]

REVIEWS = [
    {"id": "r1", "type": "Duplicate place detected", "title": "Blue Bottle Shibuya vs Blue Bottle Coffee",
     "city": "Tokyo", "country": "Japan", "category": "Cafe", "confidence": 0.92,
     "explanation": "Two extractions point to the same coordinates within 30m.",
     "source": "Text", "suggested_action": "Merge Duplicate",
     "image": IMG("1453614512568-c4024d13c247", 400, 300), "place_ids": ["p9"]},
    {"id": "r2", "type": "Low confidence extraction", "title": "Unnamed café from screenshot",
     "city": "Tokyo?", "country": "Japan", "category": "Cafe", "confidence": 0.41,
     "explanation": "OCR could not resolve a venue name. Closest match via RAG: Fuglen Tokyo.",
     "source": "Screenshot", "suggested_action": "Edit",
     "image": IMG("1511920170033-f8396924c348", 400, 300), "place_ids": []},
    {"id": "r3", "type": "Possible closed/outdated place", "title": "Bear Pond Espresso",
     "city": "Tokyo", "country": "Japan", "category": "Cafe", "confidence": 0.68,
     "explanation": "Web verification returned conflicting opening hours.",
     "source": "Article", "suggested_action": "Confirm",
     "image": IMG("1495474472287-4d71bcdd2085", 400, 300), "place_ids": []},
    {"id": "r4", "type": "Missing category", "title": "Tokyo Photographers' Gallery",
     "city": "Tokyo", "country": "Japan", "category": "Other", "confidence": 0.74,
     "explanation": "Category classifier was unsure between Museum and Gallery.",
     "source": "Text", "suggested_action": "Edit",
     "image": IMG("1542051841857-5f90071e7989", 400, 300), "place_ids": []},
    {"id": "r5", "type": "Search unavailable — saved as draft", "title": "Kissa You Ginza",
     "city": "Tokyo", "country": "Japan", "category": "Cafe", "confidence": 0.6,
     "explanation": "Verification tool was unavailable. Saved as Unverified draft.",
     "source": "Screenshot", "suggested_action": "Confirm",
     "image": IMG("1517248135467-4c7edcad34c4", 400, 300), "place_ids": []},
]

UPLOADS = [
    {"id": "u1", "title": "Tokyo café — screenshot", "source": "Screenshot", "status": "Extracting places",
     "progress": 62, "image": IMG("1511920170033-f8396924c348", 400, 400), "note": "love the wood counter"},
    {"id": "u2", "title": "teamLab Planets — text lookup", "source": "Text", "status": "Classifying categories",
     "progress": 84, "image": IMG("1554118811-1e0d58224f24", 400, 400), "note": ""},
    {"id": "u3", "title": "Article — hidden Tokyo neighborhoods", "source": "Article", "status": "Completed",
     "progress": 100, "image": IMG("1528360983277-13d401cdc186", 400, 400), "note": "save Yanaka section"},
    {"id": "u4", "title": "Screenshot — café with unknown address", "source": "Screenshot",
     "status": "Fallback / Needs manual review", "progress": 100,
     "image": IMG("1453614512568-c4024d13c247", 400, 400), "note": ""},
    {"id": "u5", "title": "Nezu Museum Garden — text lookup", "source": "Text", "status": "Awaiting review",
     "progress": 100, "image": IMG("1545569341-9eb8b30979d9", 400, 400), "note": ""},
]

PREFERENCES = [
    "Likes coffee shops",
    "Prefers walkable routes",
    "Interested in architecture",
    "Enjoys hidden local places",
    "Loves aesthetic photography spots",
]

ITINERARY_DAYS = [
    {"day": 1, "theme": "Slow Morning, Neon Evening", "stops": [
        {"n": 1, "time": "08:30", "title": "Hidden Coffee Roastery", "category": "Cafe", "district": "Nakameguro",
         "travelNote": "5 min walk from station", "aestheticNote": "Quiet minimalist café perfect for a slow morning.",
         "reason": "Matches your Coffee Culture and Minimal preferences.", "source": "Saved", "verification": "Verified",
         "mood": "Slow Morning Coffee", "image": IMG("1495474472287-4d71bcdd2085", 400, 300), "lat": 35.6442, "lng": 139.6982, "placeId": "p1"},
        {"n": 2, "time": "10:30", "title": "Daikanyama T-Site", "category": "Shopping", "district": "Daikanyama",
         "travelNote": "12 min walk along canal", "aestheticNote": "Lattice shadows across the courtyard.",
         "reason": "Adjacent neighborhood — keeps morning walkable.", "source": "Saved", "verification": "Verified",
         "mood": "Architecture Walk", "image": IMG("1542051841857-5f90071e7989", 400, 300), "lat": 35.6485, "lng": 139.7031, "placeId": "p6"},
        {"n": 3, "time": "14:00", "title": "Nezu Museum Garden", "category": "Park", "district": "Aoyama",
         "travelNote": "Hibiya Line to Omotesando", "aestheticNote": "Mossy quiet — weekday best.",
         "reason": "Architecture preference + green space pacing.", "source": "RAG Similar", "verification": "Verified",
         "mood": "Hidden Courtyard", "image": IMG("1545569341-9eb8b30979d9", 400, 300), "lat": 35.6617, "lng": 139.7175, "placeId": "p5"},
        {"n": 4, "time": "19:00", "title": "Omoide Yokocho", "category": "Restaurant", "district": "Shinjuku",
         "travelNote": "Yamanote Line, 18 min", "aestheticNote": "Smoke, neon, shoulder-to-shoulder.",
         "reason": "Anchor for your neon evening mood.", "source": "Saved", "verification": "Needs Recheck",
         "mood": "Neon Evening", "image": IMG("1554797589-7241bb691973", 400, 300), "lat": 35.6938, "lng": 139.6994, "placeId": "p7"},
    ]},
    {"day": 2, "theme": "Forest & Sky", "stops": [
        {"n": 1, "time": "09:00", "title": "Meiji Jingu Forest Path", "category": "Park", "district": "Harajuku",
         "travelNote": "From Harajuku Station", "aestheticNote": "Cathedral hush, dappled light.",
         "reason": "Balances dense days with green.", "source": "Saved", "verification": "Verified",
         "mood": "Golden Hour Walk", "image": IMG("1528164344705-47542687000d", 400, 300), "lat": 35.6764, "lng": 139.6993, "placeId": "p10"},
        {"n": 2, "time": "12:30", "title": "Aoyama Flower Market Tea House", "category": "Cafe", "district": "Omotesando",
         "travelNote": "15 min walk", "aestheticNote": "Botanical pocket in the city.",
         "reason": "Cozy + photogenic stop.", "source": "Saved", "verification": "Verified",
         "mood": "Botanical Lunch", "image": IMG("1554118811-1e0d58224f24", 400, 300), "lat": 35.6654, "lng": 139.7126, "placeId": "p4"},
        {"n": 3, "time": "16:00", "title": "Shibuya Sky", "category": "Viewpoint", "district": "Shibuya",
         "travelNote": "2 stops on Ginza Line", "aestheticNote": "Golden hour to blue hour.",
         "reason": "You favor sunset viewpoints.", "source": "Verified Recommendation", "verification": "Verified",
         "mood": "Sunset View", "image": IMG("1540959733332-eab4deabeeaf", 400, 300), "lat": 35.6586, "lng": 139.7016, "placeId": "p8"},
        {"n": 4, "time": "20:00", "title": "Onibus Coffee Nakameguro", "category": "Cafe", "district": "Nakameguro",
         "travelNote": "Tokyu Toyoko Line", "aestheticNote": "Trains as a slow metronome.",
         "reason": "Wind-down espresso.", "source": "RAG Similar", "verification": "Unverified",
         "mood": "Quiet Wind-Down", "image": IMG("1453614512568-c4024d13c247", 400, 300), "lat": 35.6338, "lng": 139.6989, "placeId": "p9"},
    ]},
    {"day": 3, "theme": "Shitamachi & Old Tokyo", "stops": [
        {"n": 1, "time": "09:30", "title": "Yanaka Ginza", "category": "Neighborhood", "district": "Yanaka",
         "travelNote": "Nippori Station", "aestheticNote": "Golden-hour light, terracotta rooftops.",
         "reason": "Hidden Gems + walkable.", "source": "Saved", "verification": "Verified",
         "mood": "Old Tokyo Stroll", "image": IMG("1528360983277-13d401cdc186", 400, 300), "lat": 35.7266, "lng": 139.7677, "placeId": "p3"},
        {"n": 2, "time": "12:00", "title": "Higashiya Ginza", "category": "Cafe", "district": "Ginza",
         "travelNote": "Hibiya Line, 22 min", "aestheticNote": "Cedar, paper, single chrysanthemum.",
         "reason": "Quiet afternoon stop.", "source": "Saved", "verification": "Verified",
         "mood": "Tea & Wagashi", "image": IMG("1517248135467-4c7edcad34c4", 400, 300), "lat": 35.6717, "lng": 139.7650, "placeId": "p11"},
        {"n": 3, "time": "15:00", "title": "teamLab Planets", "category": "Museum", "district": "Toyosu",
         "travelNote": "Yurakucho Line", "aestheticNote": "Otherworldly light environments.",
         "reason": "Creative + Photography preferences.", "source": "Saved", "verification": "Verified",
         "mood": "Immersive Light", "image": IMG("1480796927426-f609979314bd", 400, 300), "lat": 35.6493, "lng": 139.7896, "placeId": "p2"},
    ]},
    {"day": 4, "theme": "Market Morning", "stops": [
        {"n": 1, "time": "07:00", "title": "Tsukiji Outer Market", "category": "Market", "district": "Tsukiji",
         "travelNote": "Hibiya Line", "aestheticNote": "Steam, shouts, neat fish rows.",
         "reason": "Anchors a market morning.", "source": "Saved", "verification": "Needs Recheck",
         "mood": "Market Morning", "image": IMG("1583224964978-2257b960c3d3", 400, 300), "lat": 35.6654, "lng": 139.7707, "placeId": "p12"},
        {"n": 2, "time": "11:00", "title": "Nezu Museum Garden", "category": "Park", "district": "Aoyama",
         "travelNote": "Transit from Tsukiji", "aestheticNote": "Tidal calm in the garden.",
         "reason": "RAG: similar green space.", "source": "RAG Similar", "verification": "Verified",
         "mood": "Tidal Calm", "image": IMG("1545569341-9eb8b30979d9", 400, 300), "lat": 35.6617, "lng": 139.7175, "placeId": "p5"},
        {"n": 3, "time": "14:30", "title": "Shibuya Sky", "category": "Viewpoint", "district": "Shibuya",
         "travelNote": "20 min transit", "aestheticNote": "Open-sky views above the city.",
         "reason": "Verified web recommendation.", "source": "Verified Recommendation", "verification": "Verified",
         "mood": "Rooftop Pause", "image": IMG("1540959733332-eab4deabeeaf", 400, 300), "lat": 35.6586, "lng": 139.7016, "placeId": "p8"},
    ]},
]

AGENT_EVENTS = [
    {"agent": "Supervisor Agent", "status": "Success", "summary": "Started itinerary planning for Tokyo, 4 days.",
     "confidence": 0.98, "tools": ["plan_route", "delegate_task"],
     "input": "workspace=jp, days=4, style=Aesthetic", "output": "Delegated to Curator → Researcher → Planner."},
    {"agent": "Curator Agent", "status": "Success", "summary": "Extracted 12 places from recent uploads.",
     "confidence": 0.91, "tools": ["parse_link", "ocr_image", "extract_places"],
     "input": "uploads=5", "output": "12 places, 9 verified, 3 awaiting review."},
    {"agent": "Researcher Agent", "status": "Success", "summary": "Verified opening hours and locations.",
     "confidence": 0.88, "tools": ["geocode_place", "verify_place_status", "rag_search"],
     "input": "12 places", "output": "10 verified, 2 flagged for recheck."},
    {"agent": "Planner Agent", "status": "Success", "summary": "Generated 4-day Tokyo route grouped by neighborhood.",
     "confidence": 0.93, "tools": ["cluster_geo", "rag_search", "score_route"],
     "input": "16 candidates", "output": "4 days × 4 stops, walkable clusters."},
    {"agent": "Verifier Agent", "status": "Needs Review", "summary": "Merged 2 duplicates, flagged 1 place for review.",
     "confidence": 0.79, "tools": ["merge_duplicates", "verify_place_status"],
     "input": "route + KB", "output": "1 duplicate pair flagged."},
    {"agent": "Researcher Agent", "status": "Fallback", "summary": "Web verification unavailable — place saved as Unverified.",
     "confidence": 0.55, "tools": ["verify_place_status"],
     "input": "Onibus Coffee Nakameguro", "output": "Saved as Unverified, will retry later."},
]


def seed_db(db: Session) -> None:
    workspaces = [
        WorkspaceModel(
            id="jp", name="Japan Autumn", flag="🇯🇵",
            country="Japan", city="Tokyo", destination="Tokyo, Japan",
        ),
        WorkspaceModel(
            id="it", name="Italy Summer", flag="🇮🇹",
            country="Italy", city="Rome", destination="Rome, Italy",
        ),
        WorkspaceModel(
            id="cn", name="China 2026", flag="🇨🇳",
            country="China", city="Shanghai", destination="Shanghai, China",
        ),
    ]
    for ws in workspaces:
        existing = db.get(WorkspaceModel, ws.id)
        if not existing:
            db.add(ws)
        else:
            existing.country = ws.country
            existing.city = ws.city
            db.add(existing)
    db.commit()

    jp = db.get(WorkspaceModel, "jp")
    if jp:
        jp.preferences = PREFERENCES
        db.add(jp)
        db.commit()

    if db.query(PlaceModel).filter(PlaceModel.workspace_id == "jp").count() == 0:
        place_models = []
        for p in PLACES:
            pm = PlaceModel(
                id=p["id"], workspace_id="jp", title=p["title"], city=p["city"], country=p["country"],
                category=p["category"], source=p["source"], confidence=p["confidence"],
                verification=p["verification"], image=p["image"], description=p["description"],
                aesthetic_note=p["aesthetic_note"], reason=p["reason"], height=p.get("height"),
                lat=p["lat"], lng=p["lng"], district=p["district"],
            )
            pm.tags = p["tags"]
            place_models.append(pm)
            db.add(pm)
        db.commit()
        bulk_upsert_places(place_models)

    if db.query(UploadModel).filter(UploadModel.workspace_id == "jp").count() == 0:
        for u in UPLOADS:
            db.add(UploadModel(
                id=u["id"], workspace_id="jp", title=u["title"], source=u["source"],
                status=u["status"], progress=u["progress"], image=u["image"], note=u.get("note", ""),
            ))
        db.commit()

    if db.query(ReviewModel).filter(ReviewModel.workspace_id == "jp").count() == 0:
        for r in REVIEWS:
            rm = ReviewModel(
                id=r["id"], workspace_id="jp", type=r["type"], title=r["title"], city=r["city"],
                country=r["country"], category=r["category"], confidence=r["confidence"],
                explanation=r["explanation"], source=r["source"], suggested_action=r["suggested_action"],
                image=r["image"],
            )
            rm.place_ids = r.get("place_ids", [])
            db.add(rm)
        db.commit()

    if db.query(ItineraryModel).filter(ItineraryModel.workspace_id == "jp").count() == 0:
        db.add(ItineraryModel(
            id=f"it{uuid.uuid4().hex[:10]}",
            workspace_id="jp",
            days_json=json.dumps(ITINERARY_DAYS, ensure_ascii=False),
            sources_summary_json=json.dumps({"saved": 12, "rag": 4, "verified": 2, "review": 1}),
            route_summary="Grouped by neighborhood to reduce travel time and preserve aesthetic flow.",
            trip_request_json=json.dumps({"days": 4, "style": "Aesthetic", "intensity": "Balanced"}),
            is_latest=True,
        ))
        db.commit()

    if db.query(AgentEventModel).filter(AgentEventModel.workspace_id == "jp").count() == 0:
        for i, e in enumerate(AGENT_EVENTS):
            ev = AgentEventModel(
                id=f"a{i+1}", workspace_id="jp", agent=e["agent"], status=e["status"],
                summary=e["summary"], confidence=e["confidence"],
                input_preview=e["input"], output_preview=e["output"],
            )
            ev.tools = e["tools"]
            db.add(ev)
        db.commit()


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
        print("Seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
