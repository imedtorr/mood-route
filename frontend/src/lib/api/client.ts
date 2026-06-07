import type {
  AgentTimelineEntry,
  ItineraryResponse,
  Place,
  PlaceUpdate,
  ReviewCard,
  TripGenerateRequest,
  Upload,
  Workspace,
  WorkspaceCreate,
} from "@/lib/types";
import { countryToFlag, defaultTripName } from "@/lib/countries";
import {
  agentTimeline,
  itinerary,
  places,
  preferences,
  reviewQueue,
  uploads,
  workspaces,
} from "@/lib/mock-data";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function resolveImageUrl(image: string): string {
  if (!image) return "";
  if (image.startsWith("http")) return image;
  return `${API_URL}${image}`;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),

  workspaces: () =>
    USE_MOCK ? Promise.resolve(workspaces) : request<Workspace[]>("/api/workspaces"),

  createWorkspace: (body: WorkspaceCreate) => {
    if (USE_MOCK) {
      const country = body.country.trim();
      const city = body.city.trim();
      const name = body.name?.trim() || defaultTripName(country);
      const flag = body.flag || countryToFlag(country);
      const ws: Workspace = {
        id: `ws${Date.now()}`,
        name,
        flag,
        country,
        city,
        destination: `${city}, ${country}`,
      };
      workspaces.push(ws);
      return Promise.resolve(ws);
    }
    return request<Workspace>("/api/workspaces", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  places: (workspaceId: string, params?: Record<string, string>) => {
    if (USE_MOCK) return Promise.resolve(places);
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Place[]>(`/api/workspaces/${workspaceId}/places${qs}`);
  },

  searchPlaces: (workspaceId: string, q: string) => {
    if (USE_MOCK) {
      const filtered = places.filter(
        (p) =>
          p.title.toLowerCase().includes(q.toLowerCase()) ||
          p.tags.some((t) => t.toLowerCase().includes(q.toLowerCase())),
      );
      return Promise.resolve({ places: filtered, query: q });
    }
    return request<{ places: Place[]; query: string }>(
      `/api/workspaces/${workspaceId}/places/search?q=${encodeURIComponent(q)}`,
    );
  },

  updatePlace: (workspaceId: string, placeId: string, body: PlaceUpdate) => {
    if (USE_MOCK) {
      const idx = places.findIndex((p) => p.id === placeId);
      if (idx === -1) throw new ApiError(404, "Place not found");
      places[idx] = { ...places[idx], ...body };
      return Promise.resolve(places[idx]);
    }
    return request<Place>(`/api/workspaces/${workspaceId}/places/${placeId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  deletePlace: (workspaceId: string, placeId: string) => {
    if (USE_MOCK) {
      const idx = places.findIndex((p) => p.id === placeId);
      if (idx === -1) throw new ApiError(404, "Place not found");
      places.splice(idx, 1);
      return Promise.resolve({ ok: true });
    }
    return request<{ ok: boolean }>(`/api/workspaces/${workspaceId}/places/${placeId}`, {
      method: "DELETE",
    });
  },

  uploads: (workspaceId: string) =>
    USE_MOCK
      ? Promise.resolve(uploads)
      : request<Upload[]>(`/api/workspaces/${workspaceId}/uploads`),

  uploadStatus: (workspaceId: string, uploadId: string) =>
    request<Upload>(`/api/workspaces/${workspaceId}/uploads/${uploadId}`),

  addUrl: (workspaceId: string, url: string, note: string) => {
    if (USE_MOCK) {
      return Promise.resolve({
        id: `u${Date.now()}`,
        title: url.slice(0, 40),
        source: url.includes("pin") ? "Pinterest" : "Article",
        time: "just now",
        progress: 8,
        status: "Parsing link" as const,
        image: uploads[0].image,
        note,
      });
    }
    return request<Upload>(`/api/workspaces/${workspaceId}/uploads/url`, {
      method: "POST",
      body: JSON.stringify({ url, note }),
    });
  },

  addFile: (workspaceId: string, file: File, note: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("note", note);
    return request<Upload>(`/api/workspaces/${workspaceId}/uploads/file`, {
      method: "POST",
      body: form,
    });
  },

  reviews: (workspaceId: string) =>
    USE_MOCK
      ? Promise.resolve(reviewQueue)
      : request<ReviewCard[]>(`/api/workspaces/${workspaceId}/review`),

  reviewAction: (
    workspaceId: string,
    reviewId: string,
    action: string,
    payload?: { edits?: Record<string, string>; mergeIntoPlaceId?: string },
  ) =>
    request(`/api/workspaces/${workspaceId}/review/${reviewId}/action`, {
      method: "POST",
      body: JSON.stringify({ action, ...payload }),
    }),

  preferences: (workspaceId: string) =>
    USE_MOCK
      ? Promise.resolve({ preferences })
      : request<{ preferences: string[] }>(`/api/workspaces/${workspaceId}/preferences`),

  updatePreferences: (workspaceId: string, preferences: string[]) =>
    USE_MOCK
      ? Promise.resolve({ preferences })
      : request<{ preferences: string[] }>(`/api/workspaces/${workspaceId}/preferences`, {
          method: "PATCH",
          body: JSON.stringify({ preferences }),
        }),

  generateTrip: (workspaceId: string, body: TripGenerateRequest) =>
    USE_MOCK
      ? Promise.resolve({
          days: itinerary,
          sourcesSummary: { saved: 12, rag: 4, verified: 2, review: 1 },
          routeSummary:
            "Grouped by neighborhood to reduce travel time and preserve aesthetic flow.",
          tripRequest: body,
        })
      : request<ItineraryResponse>(`/api/workspaces/${workspaceId}/trips/generate`, {
          method: "POST",
          body: JSON.stringify(body),
        }),

  latestTrip: (workspaceId: string) =>
    USE_MOCK
      ? Promise.resolve({
          days: itinerary,
          sourcesSummary: { saved: 12, rag: 4, verified: 2, review: 1 },
          routeSummary:
            "Grouped by neighborhood to reduce travel time and preserve aesthetic flow.",
          tripRequest: { days: 4 },
        })
      : request<ItineraryResponse>(`/api/workspaces/${workspaceId}/trips/latest`),

  agentEvents: (workspaceId: string) =>
    USE_MOCK
      ? Promise.resolve(agentTimeline)
      : request<AgentTimelineEntry[]>(`/api/workspaces/${workspaceId}/agent-events`),
};
