import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import AgentEventModel


def new_run_id() -> str:
    return f"run{uuid.uuid4().hex[:10]}"


def log_agent_event(
    db: Session,
    workspace_id: str,
    agent: str,
    status: str,
    summary: str,
    confidence: float = 0.9,
    tools: list[str] | None = None,
    input_preview: str = "",
    output_preview: str = "",
    *,
    run_id: str | None = None,
) -> AgentEventModel:
    event = AgentEventModel(
        id=f"a{uuid.uuid4().hex[:10]}",
        workspace_id=workspace_id,
        run_id=run_id,
        agent=agent,
        status=status,
        summary=summary,
        confidence=confidence,
        input_preview=input_preview,
        output_preview=output_preview,
        created_at=datetime.now(timezone.utc),
    )
    event.tools = tools or []
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_latest_run_events(db: Session, workspace_id: str) -> list[AgentEventModel]:
    latest = (
        db.query(AgentEventModel)
        .filter(
            AgentEventModel.workspace_id == workspace_id,
            AgentEventModel.run_id.isnot(None),
        )
        .order_by(AgentEventModel.created_at.desc())
        .first()
    )
    if latest and latest.run_id:
        return (
            db.query(AgentEventModel)
            .filter(
                AgentEventModel.workspace_id == workspace_id,
                AgentEventModel.run_id == latest.run_id,
            )
            .order_by(AgentEventModel.created_at.asc())
            .all()
        )

    anchor = (
        db.query(AgentEventModel)
        .filter(
            AgentEventModel.workspace_id == workspace_id,
            AgentEventModel.agent == "Supervisor Agent",
            AgentEventModel.summary.like("Started%"),
        )
        .order_by(AgentEventModel.created_at.desc())
        .first()
    )
    if not anchor:
        return []

    return (
        db.query(AgentEventModel)
        .filter(
            AgentEventModel.workspace_id == workspace_id,
            AgentEventModel.created_at >= anchor.created_at,
        )
        .order_by(AgentEventModel.created_at.asc())
        .all()
    )
