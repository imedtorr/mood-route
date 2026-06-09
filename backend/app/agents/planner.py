import asyncio
import math
from collections import defaultdict

from sqlalchemy.orm import Session

from app.agents.researcher import ensure_place_geocoded
from app.db.models import PlaceModel
from app.rag.store import search_places
from app.schemas import ItineraryDay, ItineraryStop, SourcesSummary, TripGenerateRequest
from app.services.agent_log import log_agent_event
from app.services.gigachat import gigachat_service
from app.services.routing import estimate_walk_minutes

DEFAULT_TIMES = ["08:30", "11:00", "14:00", "17:30", "20:00"]
MOOD_BY_TAG = {
    "Minimal": "Slow Morning Coffee",
    "Neon": "Neon Evening",
    "Coffee Culture": "Coffee Crawl",
    "Architecture": "Architecture Walk",
    "Hidden Gem": "Hidden Courtyard",
    "Slow Travel": "Golden Hour Walk",
    "Photography": "Sunset View",
    "Vintage": "Old Tokyo Stroll",
    "Cozy": "Botanical Lunch",
    "Creative": "Immersive Light",
    "Luxury": "Rooftop Pause",
    "Matcha": "Tea Ceremony Pause",
}

DEFAULT_THEMES = [
    "Slow Morning, Neon Evening",
    "Forest & Sky",
    "Shitamachi & Old Tokyo",
    "Market Morning",
    "Creative Districts",
    "Hidden Corners",
    "Coastal Calm",
]


def _pick_mood(place: PlaceModel, aesthetic_mode: bool) -> str | None:
    if not aesthetic_mode:
        return None
    for tag in place.tags:
        if tag in MOOD_BY_TAG:
            return MOOD_BY_TAG[tag]
    return "Curated Stop"


def _score_place(place: PlaceModel, req: TripGenerateRequest) -> float:
    score = place.confidence
    if place.verification == "Verified":
        score += 0.15
    if place.verification == "Needs Recheck":
        score -= 0.1
    for mood in req.moods:
        if mood in place.tags:
            score += 0.12
    style_map = {
        "Coffee Crawl": ["Cafe"],
        "Architecture Focus": ["Museum", "Park", "Shopping", "Landmark"],
        "Hidden Gems": ["Neighborhood", "Market", "Viewpoint"],
        "Aesthetic": ["Cafe", "Park", "Viewpoint", "Museum"],
        "Efficient": ["Landmark", "Viewpoint", "Shopping"],
    }
    preferred = style_map.get(req.style, [])
    if place.category in preferred:
        score += 0.1
    return score


def _is_routable_place(place: PlaceModel) -> bool:
    return place.confidence >= 0.5 and place.verification != "Needs Recheck"


def _has_coordinates(place: PlaceModel) -> bool:
    return place.lat is not None and place.lng is not None


async def _ensure_coordinates_for_places(
    db: Session,
    workspace_id: str,
    places: list[PlaceModel],
    *,
    run_id: str | None = None,
) -> int:
    geocoded = 0
    for index, place in enumerate(places):
        if _has_coordinates(place):
            continue
        if index > 0:
            await asyncio.sleep(1.1)
        before = place.lat
        await ensure_place_geocoded(db, place, workspace_id, run_id=run_id)
        if place.lat is not None and before is None:
            geocoded += 1
    if geocoded:
        log_agent_event(
            db,
            workspace_id,
            "Planner Agent",
            "Success",
            f"Geocoded {geocoded} place(s) before route planning.",
            confidence=0.9,
            tools=["geocode_place"],
            input_preview=f"{len(places)} candidates",
            output_preview=f"{geocoded} newly geocoded",
            run_id=run_id,
        )
    return geocoded


async def generate_itinerary(
    db: Session,
    workspace_id: str,
    places: list[PlaceModel],
    req: TripGenerateRequest,
    *,
    run_id: str | None = None,
) -> tuple[list[ItineraryDay], SourcesSummary, str]:
    await _ensure_coordinates_for_places(db, workspace_id, places, run_id=run_id)

    routable = [
        place for place in places
        if _is_routable_place(place) and _has_coordinates(place)
    ]
    if not routable:
        routable = [place for place in places if _has_coordinates(place)]

    if req.intensity == "Packed":
        target_count = len(routable)
        stops_per_day = max(1, math.ceil(target_count / req.days)) if target_count else 0
    else:
        intensity_cap = {"Relaxed": 3, "Balanced": 4}[req.intensity]
        target_count = min(len(routable), req.days * intensity_cap)
        stops_per_day = min(intensity_cap, max(1, math.ceil(target_count / req.days)))

    scored = sorted(routable, key=lambda p: _score_place(p, req), reverse=True)
    rag_ids = {pid for pid, _ in search_places(workspace_id, " ".join(req.moods or ["aesthetic travel"]), n=8)}
    selected: list[PlaceModel] = []
    seen_titles: set[str] = set()
    for p in scored:
        if len(selected) >= target_count:
            break
        key = p.title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        selected.append(p)

    if len(selected) < target_count:
        for place in routable:
            if place.id not in {item.id for item in selected} and place.title.lower() not in seen_titles:
                selected.append(place)
                seen_titles.add(place.title.lower())
            if len(selected) >= target_count:
                break

    by_district: dict[str, list[PlaceModel]] = defaultdict(list)
    for p in selected:
        district = p.district or p.city
        by_district[district].append(p)

    districts = sorted(by_district.keys(), key=lambda d: len(by_district[d]), reverse=True)
    days: list[ItineraryDay] = []
    sources = SourcesSummary()
    district_idx = 0
    day_stops_for_narrative: list[list[str]] = []

    for day_num in range(1, req.days + 1):
        day_places: list[PlaceModel] = []
        while len(day_places) < stops_per_day and district_idx < len(districts):
            d = districts[district_idx]
            remaining = [p for p in by_district[d] if p not in day_places]
            if remaining:
                day_places.extend(remaining[: stops_per_day - len(day_places)])
            if len(day_places) >= stops_per_day or not remaining:
                district_idx += 1
            if district_idx >= len(districts):
                break

        if not day_places:
            day_places = selected[(day_num - 1) * stops_per_day : day_num * stops_per_day]

        stops: list[ItineraryStop] = []
        for i, place in enumerate(day_places):
            source = "Saved"
            if place.id in rag_ids:
                source = "RAG Similar"
                sources.rag += 1
            elif place.verification == "Verified" and place.confidence > 0.9:
                source = "Verified Recommendation"
                sources.verified += 1
            else:
                sources.saved += 1
            if place.verification == "Needs Recheck":
                sources.review += 1

            travel_note = f"Explore {place.district or place.city}"
            if i > 0 and place.lat and day_places[i - 1].lat and place.lng and day_places[i - 1].lng:
                mins = await estimate_walk_minutes(
                    day_places[i - 1].lat, day_places[i - 1].lng, place.lat, place.lng
                )
                if mins and mins <= 45:
                    travel_note = f"{mins} min walk from previous stop"
                elif mins:
                    travel_note = f"~{mins} min transit"

            stops.append(
                ItineraryStop(
                    n=i + 1,
                    time=DEFAULT_TIMES[i] if i < len(DEFAULT_TIMES) else "12:00",
                    title=place.title,
                    category=place.category,
                    district=place.district or place.city,
                    travelNote=travel_note,
                    aestheticNote=place.aesthetic_note,
                    reason=place.reason or f"Matches your {req.style} preferences.",
                    source=source,
                    verification=place.verification,
                    mood=_pick_mood(place, req.aestheticMode),
                    image=place.image,
                    lat=place.lat,
                    lng=place.lng,
                    placeId=place.id,
                    address=place.address or "",
                )
            )

        day_stops_for_narrative.append([p.title for p in day_places])

        theme = DEFAULT_THEMES[(day_num - 1) % len(DEFAULT_THEMES)]
        if req.aestheticMode and stops and stops[0].mood:
            theme = f"{stops[0].mood} & {stops[-1].mood or 'Evening'}"

        days.append(ItineraryDay(day=day_num, theme=theme, stops=stops))

    summary = (
        "Grouped by neighborhood to reduce travel time and preserve aesthetic flow."
        if req.aestheticMode
        else "Optimized for walkable clusters and verified locations."
    )

    if gigachat_service.available:
        narrative = await gigachat_service.generate_route_narrative_async(
            req.city,
            req.days,
            day_stops_for_narrative,
            req.aestheticMode,
        )
        day_themes = narrative.get("dayThemes")
        if isinstance(day_themes, list) and len(day_themes) >= req.days:
            for i, day in enumerate(days):
                if isinstance(day_themes[i], str) and day_themes[i].strip():
                    days[i] = ItineraryDay(day=day.day, theme=day_themes[i].strip(), stops=day.stops)
        route_summary = narrative.get("routeSummary")
        if isinstance(route_summary, str) and route_summary.strip():
            summary = route_summary.strip()

    log_agent_event(
        db,
        workspace_id,
        "Planner Agent",
        "Success",
        f"Generated {req.days}-day route grouped by neighborhood.",
        confidence=0.93,
        tools=["cluster_geo", "rag_search", "score_route"],
        input_preview=f"{len(selected)} candidates",
        output_preview=f"{req.days} days × ~{stops_per_day} stops",
        run_id=run_id,
    )

    return days, sources, summary
