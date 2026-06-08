import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { api } from "@/lib/api/client";
import type { TripGenerateRequest, PlaceUpdate, WorkspaceCreate } from "@/lib/types";
import { useApp } from "@/lib/app-context";

const TERMINAL_UPLOAD_STATUSES = [
  "Completed",
  "Fallback / Needs manual review",
  "Awaiting review",
  "Cancelled",
] as const;

export const PROCESSED_UPLOAD_STATUSES = [
  "Completed",
  "Fallback / Needs manual review",
  "Awaiting review",
] as const;

export function useWorkspaces() {
  return useQuery({ queryKey: ["workspaces"], queryFn: api.workspaces });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkspaceCreate) => api.createWorkspace(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (workspaceId: string) => api.deleteWorkspace(workspaceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function usePlaces(filters?: { city?: string; category?: string; verification?: string }) {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["places", workspace.id, filters],
    queryFn: () =>
      api.places(workspace.id, {
        city: filters?.city || "",
        category: filters?.category || "",
        verification: filters?.verification || "",
      }),
    enabled: Boolean(workspace.id),
  });
}

export function usePlaceSearch(query: string) {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["placeSearch", workspace.id, query],
    queryFn: () => api.searchPlaces(workspace.id, query),
    enabled: Boolean(workspace.id) && query.trim().length >= 2,
  });
}

export function useUploads() {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["uploads", workspace.id],
    queryFn: () => api.uploads(workspace.id),
    enabled: Boolean(workspace.id),
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return false;
      const pending = data.some((u) => !TERMINAL_UPLOAD_STATUSES.includes(u.status));
      return pending ? 2000 : false;
    },
  });
}

/** Refreshes places/reviews when background upload processing finishes. */
export function useSyncPlacesOnUploadComplete() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  const { data: uploads = [] } = useUploads();
  const wasPending = useRef<boolean | null>(null);

  useEffect(() => {
    const pending = uploads.some((u) => !TERMINAL_UPLOAD_STATUSES.includes(u.status));
    if (wasPending.current === true && !pending) {
      qc.invalidateQueries({ queryKey: ["places", workspace.id] });
      qc.invalidateQueries({ queryKey: ["reviews", workspace.id] });
    }
    wasPending.current = pending;
  }, [uploads, workspace.id, qc]);
}

export function useReviewQueue() {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["reviews", workspace.id],
    queryFn: () => api.reviews(workspace.id),
    enabled: Boolean(workspace.id),
  });
}

export function usePreferences() {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["preferences", workspace.id],
    queryFn: () => api.preferences(workspace.id),
    enabled: Boolean(workspace.id),
  });
}

export function useAgentEvents() {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["agentEvents", workspace.id],
    queryFn: () => api.agentEvents(workspace.id),
    enabled: Boolean(workspace.id),
    refetchInterval: 3000,
  });
}

export function useLatestTrip() {
  const { workspace } = useApp();
  return useQuery({
    queryKey: ["trip", workspace.id],
    queryFn: () => api.latestTrip(workspace.id),
    enabled: Boolean(workspace.id),
    retry: false,
  });
}

export function useAddUrlUpload() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: ({ url, note }: { url: string; note: string }) =>
      api.addUrl(workspace.id, url, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uploads", workspace.id] });
      qc.invalidateQueries({ queryKey: ["agentEvents", workspace.id] });
      qc.invalidateQueries({ queryKey: ["places", workspace.id] });
    },
  });
}

export function useAddFileUpload() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: ({ file, note }: { file: File; note: string }) =>
      api.addFile(workspace.id, file, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uploads", workspace.id] });
      qc.invalidateQueries({ queryKey: ["agentEvents", workspace.id] });
      qc.invalidateQueries({ queryKey: ["places", workspace.id] });
    },
  });
}

export function useAddTextUpload() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: ({ query, note }: { query: string; note: string }) =>
      api.addText(workspace.id, query, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uploads", workspace.id] });
      qc.invalidateQueries({ queryKey: ["agentEvents", workspace.id] });
      qc.invalidateQueries({ queryKey: ["places", workspace.id] });
    },
  });
}

export function useCancelUpload() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: (uploadId: string) => api.cancelUpload(workspace.id, uploadId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uploads", workspace.id] });
      qc.invalidateQueries({ queryKey: ["agentEvents", workspace.id] });
    },
  });
}

export function useDeleteUpload() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: (uploadId: string) => api.deleteUpload(workspace.id, uploadId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["uploads", workspace.id] }),
  });
}

export function useGenerateTrip() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: (body: TripGenerateRequest) => api.generateTrip(workspace.id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trip", workspace.id] });
      qc.invalidateQueries({ queryKey: ["agentEvents", workspace.id] });
      qc.invalidateQueries({ queryKey: ["reviews", workspace.id] });
    },
  });
}

export function useReviewAction() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: ({
      reviewId,
      action,
      edits,
      mergeIntoPlaceId,
    }: {
      reviewId: string;
      action: string;
      edits?: Record<string, string>;
      mergeIntoPlaceId?: string;
    }) => api.reviewAction(workspace.id, reviewId, action, { edits, mergeIntoPlaceId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews", workspace.id] });
      qc.invalidateQueries({ queryKey: ["places", workspace.id] });
    },
  });
}

export function useUpdatePlace() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: ({ placeId, body }: { placeId: string; body: PlaceUpdate }) =>
      api.updatePlace(workspace.id, placeId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["places", workspace.id] }),
  });
}

export function useGeocodePlace() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: (placeId: string) => api.geocodePlace(workspace.id, placeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["places", workspace.id] }),
  });
}

export function useDeletePlace() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: (placeId: string) => api.deletePlace(workspace.id, placeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["places", workspace.id] });
      qc.invalidateQueries({ queryKey: ["placeSearch", workspace.id] });
      qc.invalidateQueries({ queryKey: ["reviews", workspace.id] });
    },
  });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  const { workspace } = useApp();
  return useMutation({
    mutationFn: (preferences: string[]) => api.updatePreferences(workspace.id, preferences),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["preferences", workspace.id] }),
  });
}
