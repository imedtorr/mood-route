import type { Place } from "@/lib/types";
import { resolveImageUrl } from "@/lib/api/client";
import { VerificationBadge, SourceBadge, ConfidenceBadge, CategoryBadge } from "./badges";
import { AlertTriangle, MapPin } from "lucide-react";

function hasMapCoordinates(place: Place): boolean {
  return place.lat != null && place.lng != null;
}

export function PlaceCard({ place, onClick }: { place: Place; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group block w-full overflow-hidden rounded-2xl bg-card text-left shadow-[var(--shadow-card)] ring-1 ring-border/60 transition hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div className="relative overflow-hidden">
        <img
          src={resolveImageUrl(place.image)}
          alt={place.title}
          loading="lazy"
          style={{ height: place.height ?? 300 }}
          className="w-full object-cover transition duration-500 group-hover:scale-[1.03]"
        />
        <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-2">
          <SourceBadge source={place.source} compact className="max-w-[48%] shrink-0 shadow-sm backdrop-blur-sm" />
          <VerificationBadge
            status={place.verification}
            compact
            className="max-w-[48%] shrink-0 shadow-sm backdrop-blur-sm"
          />
        </div>
      </div>
      <div className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-serif text-lg leading-tight">{place.title}</h3>
        </div>
        <div className="space-y-1 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <MapPin className="h-3 w-3 shrink-0" />
            {place.city}, {place.country}
          </div>
          {place.address ? (
            <p className="line-clamp-1 pl-[18px]">{place.address}</p>
          ) : !hasMapCoordinates(place) ? (
            <p className="flex items-center gap-1 pl-[18px] text-warning">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              Address needed for route
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-1">
          <CategoryBadge category={place.category} />
          {place.tags.slice(0, 2).map((t) => (
            <span
              key={t}
              className="rounded-md bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
            >
              {t}
            </span>
          ))}
        </div>
        <div className="flex items-center justify-between pt-1">
          <ConfidenceBadge value={place.confidence} />
        </div>
      </div>
    </button>
  );
}
