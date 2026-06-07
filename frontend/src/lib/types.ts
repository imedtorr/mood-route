export type SourceType = "Pinterest" | "Instagram" | "Screenshot" | "Article";
export type Verification = "Verified" | "Unverified" | "Needs Recheck";
export type Category =
  | "Cafe"
  | "Restaurant"
  | "Museum"
  | "Park"
  | "Hotel"
  | "Landmark"
  | "Viewpoint"
  | "Market"
  | "Neighborhood"
  | "Shopping"
  | "Waterfront"
  | "Other";

export type Place = {
  id: string;
  title: string;
  city: string;
  country: string;
  category: Category;
  tags: string[];
  source: SourceType;
  confidence: number;
  verification: Verification;
  image: string;
  description: string;
  aestheticNote: string;
  reason: string;
  height?: number;
  lat?: number | null;
  lng?: number | null;
  district?: string;
};

export type PlaceUpdate = {
  title?: string;
  city?: string;
  country?: string;
  category?: Category;
  description?: string;
  aestheticNote?: string;
  tags?: string[];
  verification?: Verification;
};

export type Workspace = {
  id: string;
  name: string;
  flag: string;
  country: string;
  city: string;
  destination: string;
};

export type WorkspaceCreate = {
  country: string;
  city: string;
  name?: string;
  flag?: string;
};

export type UploadStatus =
  | "Parsing link"
  | "OCR processing"
  | "Extracting places"
  | "Enriching details"
  | "Classifying categories"
  | "Awaiting review"
  | "Completed"
  | "Fallback / Needs manual review";

export type Upload = {
  id: string;
  title: string;
  source: SourceType;
  time: string;
  status: UploadStatus;
  progress: number;
  image: string;
  note?: string;
};

export type AgentName =
  | "Supervisor Agent"
  | "Curator Agent"
  | "Researcher Agent"
  | "Planner Agent"
  | "Verifier Agent";
export type AgentStatus = "Success" | "Fallback" | "Needs Review";

export type AgentTimelineEntry = {
  id: string;
  agent: AgentName;
  time: string;
  status: AgentStatus;
  summary: string;
  confidence: number;
  tools: string[];
  input: string;
  output: string;
};

export type ItineraryStop = {
  n: number;
  time: string;
  title: string;
  category: Category;
  district: string;
  travelNote: string;
  aestheticNote: string;
  reason: string;
  source: "Saved" | "RAG Similar" | "Verified Recommendation";
  verification: Verification;
  mood?: string;
  image: string;
  lat?: number | null;
  lng?: number | null;
  placeId?: string | null;
};

export type ItineraryDay = { day: number; theme: string; stops: ItineraryStop[] };

export type SourcesSummary = {
  saved: number;
  rag: number;
  verified: number;
  review: number;
};

export type ItineraryResponse = {
  days: ItineraryDay[];
  sourcesSummary: SourcesSummary;
  routeSummary: string;
  tripRequest: Record<string, unknown>;
};

export type ReviewCard = {
  id: string;
  type: string;
  title: string;
  city: string;
  country: string;
  category: Category;
  confidence: number;
  explanation: string;
  source: SourceType;
  suggestedAction: string;
  image: string;
  placeIds?: string[];
};

export type TripGenerateRequest = {
  city?: string;
  days?: number;
  style?: string;
  moods?: string[];
  intensity?: string;
  aestheticMode?: boolean;
};
