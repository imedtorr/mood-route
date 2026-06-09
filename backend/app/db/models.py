import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    flag: Mapped[str] = mapped_column(String(8))
    country: Mapped[str] = mapped_column(String(128), default="")
    city: Mapped[str] = mapped_column(String(128), default="")
    destination: Mapped[str] = mapped_column(String(256))
    preferences_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    places: Mapped[list["PlaceModel"]] = relationship(back_populates="workspace")
    uploads: Mapped[list["UploadModel"]] = relationship(back_populates="workspace")
    reviews: Mapped[list["ReviewModel"]] = relationship(back_populates="workspace")
    agent_events: Mapped[list["AgentEventModel"]] = relationship(back_populates="workspace")
    itineraries: Mapped[list["ItineraryModel"]] = relationship(back_populates="workspace")

    @property
    def preferences(self) -> list[str]:
        return json.loads(self.preferences_json or "[]")

    @preferences.setter
    def preferences(self, value: list[str]) -> None:
        self.preferences_json = json.dumps(value, ensure_ascii=False)


class PlaceModel(Base):
    __tablename__ = "places"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    title: Mapped[str] = mapped_column(String(256))
    city: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    verification: Mapped[str] = mapped_column(String(32), default="Unverified")
    image: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    aesthetic_note: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str] = mapped_column(String(512), default="")
    upload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    district: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["WorkspaceModel"] = relationship(back_populates="places")

    @property
    def tags(self) -> list[str]:
        return json.loads(self.tags_json or "[]")

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.tags_json = json.dumps(value, ensure_ascii=False)


class UploadModel(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    title: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(64), default="Parsing link")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    raw_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["WorkspaceModel"] = relationship(back_populates="uploads")


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    type: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(256))
    city: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32))
    suggested_action: Mapped[str] = mapped_column(String(64))
    image: Mapped[str] = mapped_column(Text, default="")
    place_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    resolved: Mapped[bool] = mapped_column(default=False)

    workspace: Mapped["WorkspaceModel"] = relationship(back_populates="reviews")

    @property
    def place_ids(self) -> list[str]:
        return json.loads(self.place_ids_json or "[]")

    @place_ids.setter
    def place_ids(self, value: list[str]) -> None:
        self.place_ids_json = json.dumps(value)


class AgentEventModel(Base):
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    input_preview: Mapped[str] = mapped_column(Text, default="")
    output_preview: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["WorkspaceModel"] = relationship(back_populates="agent_events")

    @property
    def tools(self) -> list[str]:
        return json.loads(self.tools_json or "[]")

    @tools.setter
    def tools(self, value: list[str]) -> None:
        self.tools_json = json.dumps(value)


class ItineraryModel(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    days_json: Mapped[str] = mapped_column(Text)
    sources_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    route_summary: Mapped[str] = mapped_column(Text, default="")
    trip_request_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_latest: Mapped[bool] = mapped_column(default=True)

    workspace: Mapped["WorkspaceModel"] = relationship(back_populates="itineraries")
