import type {
  ItineraryDay,
  ItineraryStop,
  ItineraryStopActionRequest,
  Place,
} from "@/lib/types";

const MOOD_BY_TAG: Record<string, string> = {
  Minimal: "Slow Morning Coffee",
  Neon: "Neon Evening",
  "Coffee Culture": "Coffee Crawl",
  Architecture: "Architecture Walk",
  "Hidden Gem": "Hidden Courtyard",
  "Slow Travel": "Golden Hour Walk",
  Photography: "Sunset View",
  Vintage: "Old Tokyo Stroll",
  Cozy: "Botanical Lunch",
  Creative: "Immersive Light",
  Luxury: "Rooftop Pause",
};

function pickMood(place: Place, aestheticMode: boolean): string | undefined {
  if (!aestheticMode) return undefined;
  for (const tag of place.tags) {
    if (MOOD_BY_TAG[tag]) return MOOD_BY_TAG[tag];
  }
  return "Curated Stop";
}

function stopSource(place: Place): ItineraryStop["source"] {
  if (place.verification === "Verified" && place.confidence > 0.9) {
    return "Verified Recommendation";
  }
  return "Saved";
}

export function placeToStop(
  place: Place,
  partial: Pick<ItineraryStop, "n" | "time" | "travelNote">,
  aestheticMode: boolean,
): ItineraryStop {
  return {
    n: partial.n,
    time: partial.time,
    title: place.title,
    category: place.category,
    district: place.district || place.city,
    travelNote: partial.travelNote,
    aestheticNote: place.aestheticNote || place.description,
    reason: place.reason || "Added from your workspace.",
    source: stopSource(place),
    verification: place.verification,
    mood: pickMood(place, aestheticMode),
    image: place.image,
    lat: place.lat,
    lng: place.lng,
    placeId: place.id,
    address: place.address,
  };
}

function renumberDay(day: ItineraryDay): ItineraryDay {
  return {
    ...day,
    stops: day.stops.map((stop, i) => ({ ...stop, n: i + 1 })),
  };
}

function findDay(days: ItineraryDay[], dayNum: number): { index: number; day: ItineraryDay } {
  const index = days.findIndex((d) => d.day === dayNum);
  if (index === -1) throw new Error("Day not found");
  return { index, day: days[index] };
}

function findStop(day: ItineraryDay, stopN: number): { index: number; stop: ItineraryStop } {
  const index = day.stops.findIndex((s) => s.n === stopN);
  if (index === -1) throw new Error("Stop not found");
  return { index, stop: day.stops[index] };
}

export function applyItineraryStopAction(
  days: ItineraryDay[],
  body: ItineraryStopActionRequest,
  places: Place[],
  aestheticMode: boolean,
): ItineraryDay[] {
  const next = days.map((d) => ({ ...d, stops: [...d.stops] }));
  const { index: dayIdx, day } = findDay(next, body.day);
  const { index: stopIdx, stop } = findStop(day, body.stopN);

  if (body.action === "remove") {
    next[dayIdx] = renumberDay({
      ...day,
      stops: day.stops.filter((_, i) => i !== stopIdx),
    });
    return next;
  }

  if (body.action === "move") {
    if (!body.targetDay) throw new Error("targetDay is required");
    if (body.targetDay === body.day) throw new Error("Stop is already on this day");

    const { index: tgtIdx, day: tgtDay } = findDay(next, body.targetDay);
    next[dayIdx] = renumberDay({
      ...day,
      stops: day.stops.filter((_, i) => i !== stopIdx),
    });
    next[tgtIdx] = renumberDay({
      ...tgtDay,
      stops: [...next[tgtIdx].stops, stop],
    });
    return next;
  }

  if (body.action === "replace") {
    if (!body.placeId) throw new Error("placeId is required");
    const place = places.find((p) => p.id === body.placeId);
    if (!place) throw new Error("Place not found");

    const newStop = placeToStop(
      place,
      { n: stop.n, time: stop.time, travelNote: stop.travelNote },
      aestheticMode,
    );
    const stops = [...day.stops];
    stops[stopIdx] = newStop;
    next[dayIdx] = { ...day, stops };
    return next;
  }

  throw new Error("Unknown action");
}
