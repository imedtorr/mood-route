from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_workspaces() -> None:
    from sqlalchemy import inspect, text

    from app.db.models import WorkspaceModel
    from app.services.countries import parse_destination

    inspector = inspect(engine)
    if "workspaces" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("workspaces")}
    with engine.begin() as conn:
        if "country" not in cols:
            conn.execute(text("ALTER TABLE workspaces ADD COLUMN country VARCHAR(128) DEFAULT ''"))
        if "city" not in cols:
            conn.execute(text("ALTER TABLE workspaces ADD COLUMN city VARCHAR(128) DEFAULT ''"))
        if "updated_at" not in cols:
            conn.execute(text("ALTER TABLE workspaces ADD COLUMN updated_at DATETIME"))

    db = SessionLocal()
    try:
        for ws in db.query(WorkspaceModel).all():
            if ws.country and ws.city:
                continue
            city, country = parse_destination(ws.destination)
            if city:
                ws.city = city
            if country:
                ws.country = country
            db.add(ws)
        db.commit()

        cols = {c["name"] for c in inspect(engine).get_columns("workspaces")}
        if "updated_at" in cols:
            from app.services.workspaces import backfill_workspace_updated_at

            needs_backfill = db.query(WorkspaceModel).filter(WorkspaceModel.updated_at.is_(None)).count()
            if needs_backfill:
                backfill_workspace_updated_at(db)
    finally:
        db.close()


def _migrate_places() -> None:
    from datetime import datetime, timezone

    from sqlalchemy import inspect, text

    from app.db.models import PlaceModel, UploadModel

    inspector = inspect(engine)
    if "places" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("places")}
    with engine.begin() as conn:
        if "address" not in cols:
            conn.execute(text("ALTER TABLE places ADD COLUMN address VARCHAR(512) DEFAULT ''"))
        if "created_at" not in cols:
            conn.execute(text("ALTER TABLE places ADD COLUMN created_at DATETIME"))

    db = SessionLocal()
    try:
        uploads = {
            u.id: u.created_at
            for u in db.query(UploadModel).filter(UploadModel.created_at.isnot(None)).all()
        }
        fallback = datetime.now(timezone.utc)
        changed = False
        for place in db.query(PlaceModel).filter(PlaceModel.created_at.is_(None)).all():
            place.created_at = uploads.get(place.upload_id) if place.upload_id else None
            if place.created_at is None:
                place.created_at = fallback
            changed = True
        if changed:
            db.commit()
    finally:
        db.close()


def _migrate_agent_events() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "agent_events" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("agent_events")}
    with engine.begin() as conn:
        if "run_id" not in cols:
            conn.execute(text("ALTER TABLE agent_events ADD COLUMN run_id VARCHAR(64)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_events_run_id ON agent_events (run_id)"))


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_workspaces()
    _migrate_places()
    _migrate_agent_events()
