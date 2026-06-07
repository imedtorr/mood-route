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
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_workspaces()
