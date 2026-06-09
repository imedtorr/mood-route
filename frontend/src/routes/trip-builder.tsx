import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { useApp } from "@/lib/app-context";
import { useGenerateTrip, usePlaces, usePreferences, useUpdatePreferences } from "@/lib/api/hooks";
import { Sparkles, Wand2, X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/trip-builder")({
  head: () => ({ meta: [{ title: "Trip Builder — MoodRoute" }] }),
  component: TripBuilder,
});

const styles = ["Efficient", "Aesthetic", "Hidden Gems", "Coffee Crawl", "Architecture Focus"];
const moods = ["Minimal", "Neon", "Cozy", "Luxury", "Vintage", "Creative", "Slow Travel"];
const intensities = ["Relaxed", "Balanced", "Packed"];
const INTENSITY_CAP: Record<string, number> = { Relaxed: 3, Balanced: 4, Packed: 5 };

function capHint(days: number, intensity: string, poolLength: number): string {
  const packedCapacity = days * INTENSITY_CAP.Packed;
  if (intensity !== "Packed" && poolLength <= packedCapacity) {
    return "To include more places, set intensity to Packed.";
  }
  if (poolLength > packedCapacity) {
    return "To include more places, increase trip length.";
  }
  return "To include more places, increase trip length or set intensity to Packed.";
}

function TripBuilder() {
  const navigate = useNavigate();
  const { workspace, aesthetic } = useApp();
  const { data: places = [] } = usePlaces();
  const { data: prefData } = usePreferences();
  const updatePrefs = useUpdatePreferences();
  const generateTrip = useGenerateTrip();

  const [days, setDays] = useState(4);
  const [style, setStyle] = useState("Aesthetic");
  const [intensity, setIntensity] = useState("Balanced");
  const [activeMoods, setActiveMoods] = useState<string[]>(["Minimal", "Slow Travel"]);
  const [prefs, setPrefs] = useState<string[]>([]);

  useEffect(() => {
    if (prefData?.preferences) setPrefs(prefData.preferences);
  }, [prefData]);

  const verified = places.filter((p) => p.verification === "Verified").length;
  const routable = places.filter(
    (p) => p.verification !== "Needs Recheck" && (p.confidence ?? 0) >= 0.5,
  );
  const pool = routable.length > 0 ? routable : places;
  const intensityCap = INTENSITY_CAP[intensity] ?? 4;
  const itineraryCap = days * intensityCap;
  const estimate = pool.length === 0 ? 0 : Math.min(pool.length, itineraryCap);
  const stopsPerDay =
    estimate === 0 ? 0 : Math.min(intensityCap, Math.ceil(estimate / days));
  const isCappedByTrip = pool.length > 0 && estimate < pool.length;
  const excludedFromPool = places.length - pool.length;

  async function handleGenerate() {
    try {
      await generateTrip.mutateAsync({
        city: workspace.destination,
        days,
        style,
        moods: activeMoods,
        intensity,
        aestheticMode: aesthetic,
      });
      toast.success("Itinerary generated!");
      navigate({ to: "/route-planner" });
    } catch {
      toast.error("Failed to generate itinerary");
    }
  }

  function removePref(p: string) {
    const next = prefs.filter((x) => x !== p);
    setPrefs(next);
    updatePrefs.mutate(next);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Trip Builder"
        title="Compose your itinerary"
        description="MoodRoute's Supervisor Agent will coordinate planning, verification, and route generation from your workspace knowledge base."
      />

      <div className="grid gap-6 px-8 py-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-card)]">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                  Active workspace
                </div>
                <div className="mt-1 font-serif text-2xl">
                  {workspace.flag} {workspace.destination}
                </div>
              </div>
              <div className="flex gap-6 text-sm">
                <Stat label="Saved places" value={places.length} />
                <Stat label="Verified" value={verified} />
                <Stat label="In review" value={places.length - verified} />
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-card)]">
            <SectionTitle>Trip duration</SectionTitle>
            <div className="mt-3 flex items-center gap-4">
              <input
                type="range"
                min={1}
                max={7}
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="flex-1 accent-primary"
              />
              <div className="w-20 rounded-lg bg-muted px-3 py-1.5 text-center font-serif text-lg">
                {days} days
              </div>
            </div>

            <SectionTitle className="mt-6">Travel style</SectionTitle>
            <ChipGroup options={styles} value={style} onChange={setStyle} />

            <SectionTitle className="mt-6">Mood</SectionTitle>
            <div className="mt-2 flex flex-wrap gap-2">
              {moods.map((m) => {
                const on = activeMoods.includes(m);
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() =>
                      setActiveMoods(on ? activeMoods.filter((x) => x !== m) : [...activeMoods, m])
                    }
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs transition",
                      on
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-card hover:bg-muted",
                    )}
                  >
                    {m}
                  </button>
                );
              })}
            </div>

            <SectionTitle className="mt-6">Route intensity</SectionTitle>
            <ChipGroup options={intensities} value={intensity} onChange={setIntensity} />
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-card)]">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h3 className="font-serif text-lg">Workspace memory</h3>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Learned travel preferences for {workspace.name}. Edit anytime — your agents adapt.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {prefs.map((p) => (
                <span
                  key={p}
                  className="group inline-flex items-center gap-1 rounded-full border border-border bg-background px-3 py-1.5 text-xs"
                >
                  {p}
                  <button
                    type="button"
                    onClick={() => removePref(p)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <div
            className={cn(
              "sticky top-20 rounded-2xl border p-6 shadow-[var(--shadow-card)]",
              aesthetic
                ? "border-primary/30 bg-gradient-to-br from-card to-accent/40"
                : "border-border bg-card",
            )}
          >
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Estimated selection
            </div>
            <div className="mt-1 font-serif text-3xl">
              {isCappedByTrip
                ? `${estimate} of ${pool.length} places`
                : `${estimate} place${estimate === 1 ? "" : "s"}`}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {pool.length === 0
                ? "Add places to your knowledge base to build an itinerary."
                : isCappedByTrip
                  ? `Your ${days}-day ${intensity} itinerary fits ~${stopsPerDay} stop${stopsPerDay === 1 ? "" : "s"} per day (max ${itineraryCap}). ${pool.length} saved place${pool.length === 1 ? "" : "s"} available in ${workspace.destination}.`
                  : `All ${pool.length} saved place${pool.length === 1 ? "" : "s"} in ${workspace.destination} can be included.`}
            </p>
            {isCappedByTrip && (
              <p className="mt-2 rounded-lg bg-muted/60 px-3 py-2 text-[11px] text-muted-foreground">
                {capHint(days, intensity, pool.length)}
              </p>
            )}
            {excludedFromPool > 0 && (
              <p className="mt-2 text-[11px] text-amber-700 dark:text-amber-400">
                {excludedFromPool} saved place{excludedFromPool === 1 ? "" : "s"} excluded — low
                confidence or needs recheck.
              </p>
            )}

            <div className="mt-4 space-y-2 text-xs">
              <Row label="Trip length" value={`${days} days`} />
              <Row label="Style" value={style} />
              <Row label="Intensity" value={intensity} />
              <Row label="Moods" value={activeMoods.join(", ") || "—"} />
            </div>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={generateTrip.isPending || places.length === 0}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Wand2 className="h-4 w-4" />
              {generateTrip.isPending ? "Generating…" : "Generate Itinerary"}
            </button>
            <p className="mt-3 text-center text-[11px] text-muted-foreground">
              Supervisor Agent will coordinate planning, verification, and route generation.
            </p>

            {aesthetic && (
              <div className="mt-4 rounded-xl bg-background/60 p-3 font-serif text-sm italic text-muted-foreground">
                &ldquo;A slow morning, a hidden courtyard, neon at dusk.&rdquo;
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function SectionTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "text-[10px] font-medium uppercase tracking-widest text-muted-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}
function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="font-serif text-2xl leading-none">{value}</div>
      <div className="mt-1 text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
    </div>
  );
}
function ChipGroup({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={cn(
            "rounded-lg border px-3 py-1.5 text-xs transition",
            o === value
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-card hover:bg-muted",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 pb-1.5 last:border-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
