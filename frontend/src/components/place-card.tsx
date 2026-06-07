import type { Place } from "@/lib/mock-data";
import { resolveImageUrl } from "@/lib/api/client";
import { VerificationBadge, SourceBadge, ConfidenceBadge, CategoryBadge } from "./badges";
import { MapPin } from "lucide-react";

export function PlaceCard({ place, onClick }: { place: Place; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="masonry-item group block w-full overflow-hidden rounded-2xl bg-card text-left shadow-[var(--shadow-card)] ring-1 ring-border/60 transition hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div className="relative overflow-hidden">
        <img
          src={resolveImageUrl(place.image)}
          alt={place.title}
          loading="lazy"
          style={{ height: place.height ?? 300 }}
          className="w-full object-cover transition duration-500 group-hover:scale-[1.03]"
        />
        <div className="absolute left-2 top-2 flex gap-1">
          <SourceBadge source={place.source} />
        </div>
        <div className="absolute right-2 top-2">
          <VerificationBadge status={place.verification} />
        </div>
      </div>
      <div className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-serif text-lg leading-tight">{place.title}</h3>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3" />
          {place.city}, {place.country}
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
