from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["Screenshot", "Article", "Text"]
Verification = Literal["Verified", "Unverified", "Needs Recheck"]
Category = Literal[
    "Cafe", "Restaurant", "Museum", "Park", "Hotel",
    "Landmark", "Viewpoint", "Market", "Neighborhood",
    "Shopping", "Waterfront", "Other",
]
UploadStatus = Literal[
    "Parsing link", "OCR processing", "Extracting places",
    "Enriching details", "Classifying categories",
    "Awaiting review", "Completed", "Fallback / Needs manual review",
    "Cancelled",
]
AgentName = Literal[
    "Supervisor Agent", "Curator Agent", "Researcher Agent",
    "Planner Agent", "Verifier Agent",
]
AgentStatus = Literal["Success", "Fallback", "Needs Review"]
StopSource = Literal["Saved", "RAG Similar", "Verified Recommendation"]


class Workspace(BaseModel):
    id: str
    name: str
    flag: str
    country: str
    city: str
    destination: str
    updatedAt: str | None = None


class WorkspaceCreate(BaseModel):
    country: str = Field(min_length=1, max_length=128)
    city: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=128)
    flag: str | None = Field(default=None, max_length=8)


class Place(BaseModel):
    id: str
    title: str
    city: str
    country: str
    category: str
    tags: list[str]
    source: str
    confidence: float
    verification: str
    image: str
    description: str
    aestheticNote: str
    reason: str
    height: int | None = None
    lat: float | None = None
    lng: float | None = None
    district: str = ""
    address: str = ""
    sourceUrl: str | None = None


class Upload(BaseModel):
    id: str
    title: str
    source: str
    time: str
    status: str
    progress: int
    image: str
    note: str = ""
    placeIds: list[str] = []


class AgentTimelineEntry(BaseModel):
    id: str
    agent: str
    time: str
    status: str
    summary: str
    confidence: float
    tools: list[str]
    input: str
    output: str


class ItineraryStop(BaseModel):
    n: int
    time: str
    title: str
    category: str
    district: str
    travelNote: str
    aestheticNote: str
    reason: str
    source: str
    verification: str
    mood: str | None = None
    image: str
    lat: float | None = None
    lng: float | None = None
    placeId: str | None = None
    address: str = ""


class ItineraryDay(BaseModel):
    day: int
    theme: str
    stops: list[ItineraryStop]


class SourcesSummary(BaseModel):
    saved: int = 0
    rag: int = 0
    verified: int = 0
    review: int = 0


class ItineraryResponse(BaseModel):
    days: list[ItineraryDay]
    sourcesSummary: SourcesSummary
    routeSummary: str = ""
    tripRequest: dict = Field(default_factory=dict)


class ReviewCard(BaseModel):
    id: str
    type: str
    title: str
    city: str
    country: str
    category: str
    confidence: float
    explanation: str
    source: str
    suggestedAction: str
    image: str
    placeIds: list[str] = Field(default_factory=list)


class TripGenerateRequest(BaseModel):
    city: str = "Tokyo, Japan"
    days: int = Field(default=4, ge=1, le=7)
    style: str = "Aesthetic"
    moods: list[str] = Field(default_factory=list)
    intensity: str = "Balanced"
    aestheticMode: bool = False


class ReviewActionRequest(BaseModel):
    action: Literal["confirm", "edit", "merge", "reject"]
    edits: dict | None = None
    mergeIntoPlaceId: str | None = None


class PreferencesUpdate(BaseModel):
    preferences: list[str]


class UrlUploadRequest(BaseModel):
    url: str
    note: str = ""


class TextUploadRequest(BaseModel):
    query: str = Field(min_length=1, max_length=256)
    note: str = ""


class PlaceSearchResult(BaseModel):
    places: list[Place]
    query: str


class PlaceUpdate(BaseModel):
    title: str | None = None
    city: str | None = None
    country: str | None = None
    category: str | None = None
    description: str | None = None
    aestheticNote: str | None = None
    tags: list[str] | None = None
    verification: str | None = None
    address: str | None = None
