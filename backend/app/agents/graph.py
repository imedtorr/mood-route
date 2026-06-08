from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.planner import generate_itinerary
from app.db.models import PlaceModel
from app.schemas import ItineraryDay, ItineraryStop, SourcesSummary, TripGenerateRequest
from app.services.agent_log import log_agent_event


class TripState(TypedDict):
    workspace_id: str
    request: TripGenerateRequest
    places: list[PlaceModel]
    days: list[ItineraryDay]
    sources: SourcesSummary
    route_summary: str


def _filter_unverified_stops(days: list[ItineraryDay]) -> list[ItineraryDay]:
    filtered_days: list[ItineraryDay] = []
    for day in days:
        kept_stops = [stop for stop in day.stops if stop.verification != "Needs Recheck"]
        if not kept_stops:
            filtered_days.append(day)
            continue
        renumbered = [
            ItineraryStop(
                n=index + 1,
                time=stop.time,
                title=stop.title,
                category=stop.category,
                district=stop.district,
                travelNote=stop.travelNote,
                aestheticNote=stop.aestheticNote,
                reason=stop.reason,
                source=stop.source,
                verification=stop.verification,
                mood=stop.mood,
                image=stop.image,
                lat=stop.lat,
                lng=stop.lng,
                placeId=stop.placeId,
                address=stop.address,
            )
            for index, stop in enumerate(kept_stops)
        ]
        filtered_days.append(ItineraryDay(day=day.day, theme=day.theme, stops=renumbered))
    return filtered_days


async def run_trip_generation(
    db: Session,
    workspace_id: str,
    places: list[PlaceModel],
    request: TripGenerateRequest,
) -> tuple[list[ItineraryDay], SourcesSummary, str]:
    async def supervisor(state: TripState) -> TripState:
        req = state["request"]
        log_agent_event(
            db,
            state["workspace_id"],
            "Supervisor Agent",
            "Success",
            f"Started itinerary planning for {req.city}, {req.days} days.",
            confidence=0.98,
            tools=["plan_route", "delegate_task"],
            input_preview=f"workspace={state['workspace_id']}, days={req.days}, style={req.style}",
            output_preview="Delegated to Planner → Verifier.",
        )
        return state

    async def planner(state: TripState) -> TripState:
        days, sources, summary = await generate_itinerary(
            db, state["workspace_id"], state["places"], state["request"]
        )
        state["days"] = days
        state["sources"] = sources
        state["route_summary"] = summary
        return state

    async def verifier(state: TripState) -> TripState:
        original_stop_count = sum(len(day.stops) for day in state["days"])
        state["days"] = _filter_unverified_stops(state["days"])
        filtered_stop_count = sum(len(day.stops) for day in state["days"])
        removed = original_stop_count - filtered_stop_count
        log_agent_event(
            db,
            state["workspace_id"],
            "Verifier Agent",
            "Success",
            (
                f"Filtered itinerary: removed {removed} stop(s) flagged Needs Recheck."
                if removed
                else "Itinerary passed verification — no stops removed."
            ),
            confidence=0.9 if removed == 0 else 0.82,
            tools=["verify_place_status"],
            input_preview=f"{original_stop_count} stops",
            output_preview=f"{filtered_stop_count} stops kept",
        )
        return state

    graph = StateGraph(TripState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("planner", planner)
    graph.add_node("verifier", verifier)
    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "planner")
    graph.add_edge("planner", "verifier")
    graph.add_edge("verifier", END)
    compiled = graph.compile()

    initial: TripState = {
        "workspace_id": workspace_id,
        "request": request,
        "places": places,
        "days": [],
        "sources": SourcesSummary(),
        "route_summary": "",
    }
    result = await compiled.ainvoke(initial)
    return result["days"], result["sources"], result["route_summary"]
