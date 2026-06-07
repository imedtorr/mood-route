import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense, useState } from "react";
import { PageHeader } from "@/components/page-header";
import { useLatestTrip } from "@/lib/api/hooks";
import { resolveImageUrl } from "@/lib/api/client";
import { useApp } from "@/lib/app-context";
import { itinerary as mockItinerary } from "@/lib/mock-data";
import { VerificationBadge, SourceBadge, CategoryBadge } from "@/components/badges";
import { Clock, MapPin, MoreHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const MapPanel = lazy(() =>
  import("@/components/map/map-panel").then((m) => ({ default: m.MapPanel })),
);

export const Route = createFileRoute("/route-planner")({
  head: () => ({ meta: [{ title: "Route Planner — MoodRoute" }] }),
  component: RoutePlanner,
});

function RoutePlanner() {
  const { aesthetic } = useApp();
  const { data: trip, isLoading, isError } = useLatestTrip();
  const [dayIdx, setDayIdx] = useState(0);

  const days = trip?.days ?? (isError ? mockItinerary : []);
  const sources = trip?.sourcesSummary ?? { saved: 12, rag: 4, verified: 2, review: 1 };
  const routeSummary =
    trip?.routeSummary ??
    "Grouped by neighborhood to reduce travel time and preserve aesthetic flow.";
  const day = days[dayIdx] ?? days[0];

  if (isLoading && !trip) {
    return <div className="px-8 py-16 text-center text-muted-foreground">Loading itinerary…</div>;
  }

  if (!day) {
    return (
      <div className="px-8 py-16 text-center">
        <p className="font-serif text-xl">No itinerary yet</p>
        <p className="mt-2 text-sm text-muted-foreground">Generate one from Trip Builder.</p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Route Planner"
        title={`${days.length} days in Tokyo`}
        description={routeSummary}
      />

      <div className="grid gap-6 px-8 py-8 lg:grid-cols-[120px_1fr_360px]">
        <aside className="space-y-1 lg:sticky lg:top-20 lg:self-start">
          {days.map((d, i) => (
            <button
              key={d.day}
              type="button"
              onClick={() => setDayIdx(i)}
              className={cn(
                "block w-full rounded-xl px-4 py-3 text-left transition",
                i === dayIdx ? "bg-primary text-primary-foreground" : "bg-card hover:bg-muted",
              )}
            >
              <div className="text-[10px] uppercase tracking-widest opacity-70">Day</div>
              <div className="font-serif text-2xl leading-none">{d.day}</div>
              <div className="mt-1 text-[11px] leading-tight opacity-80">{d.theme}</div>
            </button>
          ))}
        </aside>

        <section>
          {aesthetic && day.stops[0]?.mood && (
            <div className="mb-4 rounded-2xl border border-primary/30 bg-accent/40 p-4 font-serif text-base italic text-foreground/80">
              {day.theme} — &ldquo;{day.stops[0].mood}&rdquo; into &ldquo;
              {day.stops[day.stops.length - 1].mood}&rdquo;
            </div>
          )}
          <ol className="relative space-y-4">
            {day.stops.map((s, i) => (
              <li key={s.n} className="relative">
                {i < day.stops.length - 1 && (
                  <span className="absolute left-[19px] top-12 h-[calc(100%+8px)] w-px bg-border" />
                )}
                <div className="flex gap-4">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-card font-serif text-lg shadow-sm">
                    {s.n}
                  </div>
                  <article className="flex-1 overflow-hidden rounded-2xl border border-border bg-card shadow-[var(--shadow-card)]">
                    <div className="grid md:grid-cols-[200px_1fr]">
                      <img src={resolveImageUrl(s.image)} alt="" className="h-full w-full object-cover md:h-44" />
                      <div className="space-y-3 p-5">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Clock className="h-3 w-3" /> {s.time}
                              <span>•</span>
                              <MapPin className="h-3 w-3" /> {s.district}
                            </div>
                            <h3 className="mt-1 font-serif text-2xl leading-tight">{s.title}</h3>
                          </div>
                          <button
                            type="button"
                            className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </button>
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <CategoryBadge category={s.category} />
                          <SourceBadge source={s.source} />
                          <VerificationBadge status={s.verification} />
                          {aesthetic && s.mood && (
                            <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-medium italic text-primary">
                              {s.mood}
                            </span>
                          )}
                        </div>
                        <p
                          className={cn(
                            "text-sm text-foreground/80",
                            aesthetic && "font-serif italic",
                          )}
                        >
                          {aesthetic ? `"${s.aestheticNote}"` : s.travelNote}
                        </p>
                        <div className="rounded-lg bg-muted/60 p-2.5 text-xs">
                          <span className="font-medium text-foreground">Why this stop · </span>
                          <span className="text-muted-foreground">{s.reason}</span>
                        </div>
                      </div>
                    </div>
                  </article>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-8 rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-card)]">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h3 className="font-serif text-xl">Sources used</h3>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Orchestrated by Supervisor Agent</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SourceTile
                n={sources.saved}
                label="Saved places"
                tone="bg-secondary text-secondary-foreground"
              />
              <SourceTile
                n={sources.rag}
                label="RAG similar"
                tone="bg-[oklch(0.94_0.05_285)] text-[oklch(0.4_0.16_285)]"
              />
              <SourceTile
                n={sources.verified}
                label="Verified recs"
                tone="bg-success/15 text-success"
              />
              <SourceTile
                n={sources.review}
                label="Flagged for review"
                tone="bg-warning/15 text-warning"
              />
            </div>
            <p className="mt-4 rounded-xl bg-muted/60 p-3 text-sm italic text-muted-foreground">
              &ldquo;{routeSummary}&rdquo;
            </p>
          </div>
        </section>

        <aside className="lg:sticky lg:top-20 lg:self-start">
          <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[var(--shadow-card)]">
            <div className="border-b border-border px-4 py-3">
              <div className="font-serif text-lg">Day {day.day} route</div>
              <div className="text-xs text-muted-foreground">
                {day.stops.length} stops · walkable cluster
              </div>
            </div>
            <Suspense
              fallback={
                <div className="flex h-[420px] items-center justify-center text-sm text-muted-foreground">
                  Loading map…
                </div>
              }
            >
              <MapPanel stops={day.stops} />
            </Suspense>
            <div className="space-y-1 p-4 text-xs">
              {day.stops.map((s) => (
                <div key={s.n} className="flex items-center gap-2">
                  <span className="grid h-5 w-5 place-items-center rounded-full bg-primary text-[10px] text-primary-foreground">
                    {s.n}
                  </span>
                  <span className="truncate">{s.title}</span>
                  <span className="ml-auto text-muted-foreground">{s.time}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function SourceTile({ n, label, tone }: { n: number; label: string; tone: string }) {
  return (
    <div className="rounded-xl border border-border bg-background p-3">
      <div
        className={cn(
          "inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium",
          tone,
        )}
      >
        {n}
      </div>
      <div className="mt-2 text-sm font-medium">{label}</div>
    </div>
  );
}
