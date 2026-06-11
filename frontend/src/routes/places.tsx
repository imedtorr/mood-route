import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { SortablePlaceGrid } from "@/components/sortable-place-grid";
import { useApp } from "@/lib/app-context";
import {
  mergePlacesOrder,
  placesToOrder,
  reorderWithVisible,
  savePlacesOrder,
} from "@/lib/places-order";
import {
  useDeletePlace,
  useEnrichPlace,
  useGeocodePlace,
  usePlaces,
  useUpdatePlace,
} from "@/lib/api/hooks";
import { ApiError, resolveImageUrl } from "@/lib/api/client";
import {
  KNOWN_AESTHETIC_TAGS,
  splitPlaceTags,
  usedAestheticFilterTags,
  type AestheticTag,
} from "@/lib/aesthetic-tags";
import type { Category, Place } from "@/lib/types";
import { cn } from "@/lib/utils";
import { VerificationBadge, CategoryBadge } from "@/components/badges";
import {
  AlertTriangle,
  ChevronDown,
  ExternalLink,
  Loader2,
  MapPinned,
  Pencil,
  Search,
  Sparkles,
  Trash2,
  X,
  MapPin,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export const Route = createFileRoute("/places")({
  validateSearch: (search: Record<string, unknown>) => ({
    placeId: typeof search.placeId === "string" ? search.placeId : undefined,
  }),
  head: () => ({ meta: [{ title: "Places — MoodRoute" }] }),
  component: PlacesPage,
});

const verifs = ["All", "Verified", "Unverified", "Needs Recheck"];

function hasMapCoordinates(place: Place): boolean {
  return place.lat != null && place.lng != null;
}

const placeCategories: Category[] = [
  "Cafe",
  "Restaurant",
  "Museum",
  "Park",
  "Hotel",
  "Landmark",
  "Viewpoint",
  "Market",
  "Neighborhood",
  "Shopping",
  "Waterfront",
  "Other",
];

function PlacesPage() {
  const { placeId } = Route.useSearch();
  const navigate = Route.useNavigate();
  const { workspace } = useApp();
  const [cat, setCat] = useState("All");
  const [tag, setTag] = useState("All");
  const [verif, setVerif] = useState("All");
  const [active, setActive] = useState<Place | null>(null);
  const [order, setOrder] = useState<string[]>([]);

  const { data: allPlaces = [] } = usePlaces();

  useEffect(() => {
    if (!workspace.id) return;
    setOrder(placesToOrder(mergePlacesOrder(workspace.id, allPlaces)));
  }, [workspace.id, allPlaces]);

  const categoryOptions = useMemo(() => ["All", ...placeCategories], []);

  const tagOptions = useMemo(() => {
    const used = usedAestheticFilterTags(allPlaces.flatMap((p) => p.tags));
    return ["All", ...used];
  }, [allPlaces]);

  useEffect(() => {
    if (!placeId || !allPlaces.length) return;
    const place = allPlaces.find((p) => p.id === placeId);
    if (!place) return;
    setActive(place);
    requestAnimationFrame(() => {
      document.getElementById(`place-${placeId}`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
  }, [placeId, allPlaces]);

  const orderedPlaces = useMemo(() => {
    const byId = new Map(allPlaces.map((p) => [p.id, p]));
    const result = order.map((id) => byId.get(id)).filter((place): place is Place => place != null);
    const inOrder = new Set(order);
    for (const place of allPlaces) {
      if (!inOrder.has(place.id)) result.unshift(place);
    }
    return result;
  }, [allPlaces, order]);

  const filtered = useMemo(
    () =>
      orderedPlaces.filter((p) => {
        if (cat !== "All" && p.category !== cat) return false;
        if (verif !== "All" && p.verification !== verif) return false;
        if (tag !== "All" && !p.tags.includes(tag)) return false;
        return true;
      }),
    [orderedPlaces, cat, verif, tag],
  );

  function handleReorder(nextFilteredOrder: string[]) {
    if (!workspace.id) return;
    const nextOrder = reorderWithVisible(order, nextFilteredOrder);
    setOrder(nextOrder);
    savePlacesOrder(workspace.id, nextOrder);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge Base"
        title="Places"
        description="Every place your AI agents extracted from saved inspiration — structured, tagged, and verifiable."
      />

      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-border bg-background px-8 py-3">
        <FilterGroup label="Category" value={cat} onChange={setCat} options={categoryOptions} />
        <FilterGroup label="Aesthetic" value={tag} onChange={setTag} options={tagOptions} />
        <FilterGroup label="Status" value={verif} onChange={setVerif} options={verifs} />
        <div className="ml-auto text-xs text-muted-foreground">{filtered.length} places</div>
      </div>

      <div className="px-8 py-6">
        <SortablePlaceGrid places={filtered} onReorder={handleReorder} onPlaceClick={setActive} />
      </div>

      {active && (
        <PlaceDrawer
          place={active}
          onClose={() => {
            setActive(null);
            if (placeId) navigate({ search: {} });
          }}
          onChange={setActive}
        />
      )}
    </div>
  );
}

function FilterGroup({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none rounded-md border border-border bg-card py-1 pl-3 pr-8 text-xs outline-none hover:bg-muted"
        >
          {options.map((o) => (
            <option key={o}>{o}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
      </div>
    </div>
  );
}

function PlaceDrawer({
  place,
  onClose,
  onChange,
}: {
  place: Place;
  onClose: () => void;
  onChange: (place: Place) => void;
}) {
  const updatePlace = useUpdatePlace();
  const deletePlace = useDeletePlace();
  const geocodePlace = useGeocodePlace();
  const enrichPlace = useEnrichPlace();
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [title, setTitle] = useState(place.title);
  const [city, setCity] = useState(place.city);
  const [country, setCountry] = useState(place.country);
  const [address, setAddress] = useState(place.address ?? "");
  const [category, setCategory] = useState<Category>(place.category);
  const [description, setDescription] = useState(place.description);
  const [aestheticNote, setAestheticNote] = useState(place.aestheticNote);
  const [selectedTags, setSelectedTags] = useState<AestheticTag[]>([]);
  const [customTagsText, setCustomTagsText] = useState("");

  useEffect(() => {
    setEditing(false);
    setTitle(place.title);
    setCity(place.city);
    setCountry(place.country);
    setAddress(place.address ?? "");
    setCategory(place.category);
    setDescription(place.description);
    setAestheticNote(place.aestheticNote);
    const { canonical, custom } = splitPlaceTags(place.tags);
    setSelectedTags(canonical);
    setCustomTagsText(custom.join(", "));
  }, [place]);

  function toggleTag(tag: AestheticTag) {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  }

  async function handleSave() {
    const customTags = customTagsText
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const tags = [...selectedTags, ...customTags];
    try {
      const updated = await updatePlace.mutateAsync({
        placeId: place.id,
        body: { title, city, country, address, category, description, aestheticNote, tags },
      });
      onChange(updated);
      setEditing(false);
      toast.success("Place updated");
    } catch {
      toast.error("Failed to update place");
    }
  }

  async function handleGeocode() {
    try {
      const updated = await geocodePlace.mutateAsync(place.id);
      onChange(updated);
      if (hasMapCoordinates(updated)) {
        toast.success("Address found and added to map");
      } else {
        toast.error("Could not find address. Try refining the name or address.");
      }
    } catch {
      toast.error("Error searching for address");
    }
  }

  async function handleEnrich() {
    try {
      const updated = await enrichPlace.mutateAsync(place.id);
      onChange(updated);
      toast.success("Place enriched via GigaChat");
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error("GigaChat is not configured — add GIGACHAT_CREDENTIALS to .env");
      } else {
        toast.error("Failed to enrich place");
      }
    }
  }

  async function handleDelete() {
    try {
      await deletePlace.mutateAsync(place.id);
      setConfirmDelete(false);
      onClose();
      toast.success("Place deleted");
    } catch {
      toast.error("Failed to delete place");
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-sm sm:p-6"
        onClick={onClose}
      >
        <div
          className="relative w-full max-w-5xl overflow-hidden rounded-xl bg-background shadow-2xl ring-1 ring-border/60"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 z-20 rounded-full bg-background/95 p-2 shadow-md ring-1 ring-border/60 transition-all hover:bg-accent hover:text-accent-foreground hover:shadow-lg active:scale-95"
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
          <div className="grid md:grid-cols-[minmax(280px,2fr)_minmax(360px,3fr)]">
            <div className="relative overflow-hidden md:min-h-[420px]">
              <img
                src={resolveImageUrl(place.image)}
                alt={place.title}
                className="h-56 w-full object-cover md:absolute md:inset-0 md:h-full"
              />
            </div>
            <div className="flex max-h-[85vh] flex-col overflow-y-auto p-6 md:max-h-none md:min-h-[420px] md:p-8">
              {editing ? (
                <div className="space-y-4">
                  <div className="space-y-3">
                    <Field label="Name">
                      <Input value={title} onChange={(e) => setTitle(e.target.value)} />
                    </Field>
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="City">
                        <Input value={city} onChange={(e) => setCity(e.target.value)} />
                      </Field>
                      <Field label="Country">
                        <Input value={country} onChange={(e) => setCountry(e.target.value)} />
                      </Field>
                    </div>
                    <Field label="Category">
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value as Category)}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      >
                        {placeCategories.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Address">
                      <Input value={address} onChange={(e) => setAddress(e.target.value)} />
                    </Field>
                    <Field label="Description">
                      <Textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        className="min-h-24 resize-none"
                      />
                    </Field>
                    <Field label="Aesthetic note">
                      <Textarea
                        value={aestheticNote}
                        onChange={(e) => setAestheticNote(e.target.value)}
                        className="min-h-20 resize-none"
                      />
                    </Field>
                    <Field label="Aesthetic tags">
                      <div className="flex flex-wrap gap-1.5">
                        {KNOWN_AESTHETIC_TAGS.map((tag) => (
                          <button
                            key={tag}
                            type="button"
                            onClick={() => toggleTag(tag)}
                            className={cn(
                              "rounded-md px-2 py-1 text-[11px] transition-colors",
                              selectedTags.includes(tag)
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-muted-foreground hover:bg-muted/80",
                            )}
                          >
                            {tag}
                          </button>
                        ))}
                      </div>
                    </Field>
                    <Field label="Custom tags (optional, comma-separated)">
                      <Input
                        value={customTagsText}
                        onChange={(e) => setCustomTagsText(e.target.value)}
                        placeholder="e.g. Rooftop, Local favorite"
                      />
                    </Field>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => setEditing(false)}
                      disabled={updatePlace.isPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      className="flex-1"
                      onClick={handleSave}
                      disabled={updatePlace.isPending}
                    >
                      {updatePlace.isPending ? "Saving…" : "Save changes"}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-0 flex-1 flex-col">
                  <header className="shrink-0 space-y-3">
                    <div>
                      <h2 className="font-serif text-3xl tracking-tight">{place.title}</h2>
                      <div className="mt-1.5 flex items-center gap-1.5 text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 shrink-0" />
                        {place.city}, {place.country}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <CategoryBadge category={place.category} />
                      <VerificationBadge status={place.verification} />
                      {hasMapCoordinates(place) ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-success/25 bg-success/12 px-2 py-0.5 text-[10px] font-medium text-success">
                          <MapPinned className="h-3 w-3" />
                          On map
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full border border-warning/35 bg-warning/15 px-2 py-0.5 text-[10px] font-medium text-warning-foreground">
                          <AlertTriangle className="h-3 w-3" />
                          Needs address
                        </span>
                      )}
                    </div>
                  </header>

                  <blockquote className="mt-6 shrink-0 border-l-2 border-primary py-1 pl-4">
                    <p className="font-serif text-lg leading-relaxed italic text-foreground/90">
                      {place.aestheticNote
                        ? `\u201C${place.aestheticNote}\u201D`
                        : "No aesthetic note yet \u2014 click Enrich below"}
                    </p>
                  </blockquote>

                  <div className="mt-6 flex-1 divide-y divide-border/60">
                    <section className="pb-5 pt-0">
                      <div className="rounded-xl border border-primary/12 bg-accent/50 p-4 ring-1 ring-inset ring-primary/5">
                        <div className="flex items-baseline justify-between gap-3">
                          <h3 className="text-[10px] font-medium uppercase tracking-widest text-accent-foreground/80">
                            About
                          </h3>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-auto shrink-0 gap-1 px-2 py-0 text-[11px] font-normal text-muted-foreground hover:bg-transparent hover:text-foreground"
                            onClick={handleEnrich}
                            disabled={enrichPlace.isPending}
                          >
                            {enrichPlace.isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Sparkles className="h-3 w-3" />
                            )}
                            Enrich
                          </Button>
                        </div>
                        <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
                          {place.description || "No description yet \u2014 click Enrich"}
                        </p>
                      </div>
                    </section>

                    <section className="py-5">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                          Location
                        </h3>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 shrink-0 gap-1 px-2 text-[11px] font-normal text-muted-foreground hover:bg-transparent hover:text-foreground"
                          onClick={handleGeocode}
                          disabled={geocodePlace.isPending}
                        >
                          {geocodePlace.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Search className="h-3 w-3" />
                          )}
                          Find
                        </Button>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-foreground/85">
                        {place.address || "Address not found \u2014 enter manually or search"}
                      </p>
                    </section>

                    <section className="py-5">
                      <h3 className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                        Origin
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-foreground/85">
                        {place.reason}
                      </p>
                      {place.sourceUrl && (
                        <a
                          href={place.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex items-start gap-1.5 text-sm text-primary hover:underline"
                        >
                          <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          <span className="break-all">{place.sourceUrl}</span>
                        </a>
                      )}
                    </section>
                  </div>

                  <footer className="mt-auto flex shrink-0 items-end justify-between gap-4 border-t border-border pt-5">
                    <div className="flex min-w-0 flex-1 flex-wrap gap-1.5">
                      {place.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        onClick={() => setEditing(true)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-3 py-1.5 text-xs font-medium shadow-sm ring-1 ring-border/50 transition-all hover:bg-accent hover:text-accent-foreground hover:shadow-md active:scale-95"
                        title="Edit place"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(true)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-3 py-1.5 text-xs font-medium shadow-sm ring-1 ring-border/50 transition-all hover:bg-destructive/15 hover:text-destructive hover:ring-destructive/30 hover:shadow-md active:scale-95"
                        title="Delete place"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </footer>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this place?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{place.title}&rdquo; will be removed from your knowledge base. This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletePlace.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleDelete();
              }}
              disabled={deletePlace.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deletePlace.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}
