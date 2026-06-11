import type { Place } from "@/lib/types";

function storageKey(workspaceId: string): string {
  return `moodroute:places-order:${workspaceId}`;
}

export function loadPlacesOrder(workspaceId: string): string[] {
  try {
    const raw = localStorage.getItem(storageKey(workspaceId));
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : [];
  } catch {
    return [];
  }
}

export function savePlacesOrder(workspaceId: string, order: string[]): void {
  localStorage.setItem(storageKey(workspaceId), JSON.stringify(order));
}

/** API returns newest-first. Saved order is kept; places not yet in saved order prepend. */
export function mergePlacesOrder(workspaceId: string, places: Place[]): Place[] {
  const saved = loadPlacesOrder(workspaceId);
  if (!saved.length) return places;

  const byId = new Map(places.map((p) => [p.id, p]));
  const result: Place[] = [];
  const seen = new Set<string>();

  for (const place of places) {
    if (!saved.includes(place.id)) {
      result.push(place);
      seen.add(place.id);
    }
  }

  for (const id of saved) {
    const place = byId.get(id);
    if (place && !seen.has(id)) {
      result.push(place);
      seen.add(id);
    }
  }

  return result;
}

export function placesToOrder(places: Place[]): string[] {
  return places.map((p) => p.id);
}

/** Reorder visible cards while keeping hidden (filtered-out) places in their slots. */
export function reorderWithVisible(fullOrder: string[], nextVisibleOrder: string[]): string[] {
  const visibleSet = new Set(nextVisibleOrder);
  const result = [...fullOrder];
  const visibleIndices = fullOrder
    .map((id, index) => (visibleSet.has(id) ? index : -1))
    .filter((index) => index >= 0);

  nextVisibleOrder.forEach((id, index) => {
    result[visibleIndices[index]!] = id;
  });

  return result;
}
