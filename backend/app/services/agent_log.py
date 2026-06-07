import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import AgentEventModel


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
) -> AgentEventModel:
    event = AgentEventModel(
        id=f"a{uuid.uuid4().hex[:10]}",
        workspace_id=workspace_id,
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
