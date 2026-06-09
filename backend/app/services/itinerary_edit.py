import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.planner import _pick_mood
from app.db.models import ItineraryModel, PlaceModel
from app.schemas import ItineraryDay, ItineraryStop, ItineraryStopActionRequest


def _load_days(it: ItineraryModel) -> list[ItineraryDay]:
    return [ItineraryDay(**d) for d in json.loads(it.days_json)]


def _save_days(it: ItineraryModel, days: list[ItineraryDay]) -> None:
    it.days_json = json.dumps([d.model_dump() for d in days], ensure_ascii=False)


def _find_day(days: list[ItineraryDay], day_num: int) -> tuple[int, ItineraryDay]:
    for i, day in enumerate(days):
        if day.day == day_num:
            return i, day
    raise HTTPException(status_code=404, detail="Day not found")


def _find_stop(day: ItineraryDay, stop_n: int) -> tuple[int, ItineraryStop]:
    for i, stop in enumerate(day.stops):
        if stop.n == stop_n:
            return i, stop
    raise HTTPException(status_code=404, detail="Stop not found")


def _renumber_day(day: ItineraryDay) -> ItineraryDay:
    stops = [stop.model_copy(update={"n": i + 1}) for i, stop in enumerate(day.stops)]
    return ItineraryDay(day=day.day, theme=day.theme, stops=stops)


def _stop_source(place: PlaceModel) -> str:
    if place.verification == "Verified" and place.confidence > 0.9:
        return "Verified Recommendation"
    return "Saved"


def _place_to_stop(
    place: PlaceModel,
    *,
    n: int,
    time: str,
    travel_note: str,
    aesthetic_mode: bool,
) -> ItineraryStop:
    return ItineraryStop(
        n=n,
        time=time,
        title=place.title,
        category=place.category,
        district=place.district or place.city,
        travelNote=travel_note,
        aestheticNote=place.aesthetic_note or place.description,
        reason=place.reason or "Added from your workspace.",
        source=_stop_source(place),
        verification=place.verification,
        mood=_pick_mood(place, aesthetic_mode),
        image=place.image,
        lat=place.lat,
        lng=place.lng,
        placeId=place.id,
        address=place.address or "",
    )


def apply_stop_action(
    db: Session,
    it: ItineraryModel,
    body: ItineraryStopActionRequest,
) -> list[ItineraryDay]:
    days = _load_days(it)
    day_idx, day = _find_day(days, body.day)
    stop_idx, stop = _find_stop(day, body.stopN)

    trip_request = json.loads(it.trip_request_json or "{}")
    aesthetic_mode = bool(trip_request.get("aestheticMode"))

    if body.action == "remove":
        new_stops = day.stops[:stop_idx] + day.stops[stop_idx + 1 :]
        days[day_idx] = _renumber_day(
            ItineraryDay(day=day.day, theme=day.theme, stops=new_stops),
        )

    elif body.action == "move":
        if body.targetDay is None:
            raise HTTPException(status_code=400, detail="targetDay is required")
        if body.targetDay == body.day:
            raise HTTPException(status_code=400, detail="Stop is already on this day")
        tgt_idx, tgt_day = _find_day(days, body.targetDay)

        new_src_stops = day.stops[:stop_idx] + day.stops[stop_idx + 1 :]
        days[day_idx] = _renumber_day(
            ItineraryDay(day=day.day, theme=day.theme, stops=new_src_stops),
        )

        new_tgt_stops = [*days[tgt_idx].stops, stop]
        days[tgt_idx] = _renumber_day(
            ItineraryDay(day=tgt_day.day, theme=tgt_day.theme, stops=new_tgt_stops),
        )

    elif body.action == "replace":
        if not body.placeId:
            raise HTTPException(status_code=400, detail="placeId is required")
        place = db.get(PlaceModel, body.placeId)
        if not place or place.workspace_id != it.workspace_id or place.status != "active":
            raise HTTPException(status_code=404, detail="Place not found")

        new_stop = _place_to_stop(
            place,
            n=stop.n,
            time=stop.time,
            travel_note=stop.travelNote,
            aesthetic_mode=aesthetic_mode,
        )
        new_stops = list(day.stops)
        new_stops[stop_idx] = new_stop
        days[day_idx] = ItineraryDay(day=day.day, theme=day.theme, stops=new_stops)

    else:
        raise HTTPException(status_code=400, detail="Unknown action")

    _save_days(it, days)
    return days
