from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.planner import generate_itinerary
from app.db.models import PlaceModel
from app.schemas import ItineraryDay, SourcesSummary, TripGenerateRequest
from app.services.agent_log import log_agent_event


class TripState(TypedDict):
    workspace_id: str
    request: TripGenerateRequest
    places: list[PlaceModel]
    days: list[ItineraryDay]
    sources: SourcesSummary
    route_summary: str


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
