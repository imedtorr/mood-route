import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { PlaceCard } from "@/components/place-card";
import { useDeletePlace, usePlaces, useUpdatePlace } from "@/lib/api/hooks";
import { resolveImageUrl } from "@/lib/api/client";
import { useApp } from "@/lib/app-context";
import type { Category, Place } from "@/lib/types";
import {
  VerificationBadge,
  SourceBadge,
  ConfidenceBadge,
  CategoryBadge,
} from "@/components/badges";
import { Pencil, Trash2, X, MapPin } from "lucide-react";
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

const cats = [
  "All",
  "Cafe",
  "Restaurant",
  "Museum",
  "Park",
  "Viewpoint",
  "Market",
  "Neighborhood",
  "Shopping",
];
const tags = [
  "All",
  "Minimal",
  "Cozy",
  "Coffee Culture",
  "Architecture",
  "Hidden Gem",
  "Vintage",
  "Slow Travel",
  "Photography",
  "Neon",
];
const verifs = ["All", "Verified", "Unverified", "Needs Recheck"];

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
  const { workspace } = useApp();
  const { placeId } = Route.useSearch();
  const navigate = Route.useNavigate();
  const [city, setCity] = useState("All");
  const [cat, setCat] = useState("All");
  const [tag, setTag] = useState("All");
  const [verif, setVerif] = useState("All");
  const [active, setActive] = useState<Place | null>(null);

  const { data: allPlaces = [] } = usePlaces();

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

  const cities = useMemo(() => {
    const options = new Set<string>(["All"]);
    const wsCity = workspace.city || workspace.destination.split(",")[0]?.trim();
    if (wsCity) options.add(wsCity);
    for (const p of allPlaces) options.add(p.city);
    return Array.from(options);
  }, [allPlaces, workspace.destination]);

  useEffect(() => {
    if (city !== "All" && !cities.includes(city)) setCity("All");
  }, [city, cities]);

  const filtered = useMemo(
    () =>
      allPlaces.filter((p) => {
        if (city !== "All" && p.city !== city) return false;
        if (cat !== "All" && p.category !== cat) return false;
        if (verif !== "All" && p.verification !== verif) return false;
        if (tag !== "All" && !p.tags.includes(tag)) return false;
        return true;
      }),
    [allPlaces, city, cat, verif, tag],
  );

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge Base"
        title="Places"
        description="Every place your AI agents extracted from saved inspiration — structured, tagged, and verifiable."
      />

      <div className="sticky top-14 z-[5] flex flex-wrap gap-2 border-b border-border bg-background/90 px-8 py-3 backdrop-blur">
        <FilterGroup label="City" value={city} onChange={setCity} options={cities} />
        <FilterGroup label="Category" value={cat} onChange={setCat} options={cats} />
        <FilterGroup label="Aesthetic" value={tag} onChange={setTag} options={tags} />
        <FilterGroup label="Status" value={verif} onChange={setVerif} options={verifs} />
        <div className="ml-auto text-xs text-muted-foreground">{filtered.length} places</div>
      </div>

      <div className="px-8 py-6">
        <div className="masonry">
          {filtered.map((p) => (
            <div key={p.id} id={`place-${p.id}`}>
              <PlaceCard place={p} onClick={() => setActive(p)} />
            </div>
          ))}
        </div>
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
    <div className="flex items-center gap-1">
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-card px-2 py-1 text-xs outline-none hover:bg-muted"
      >
        {options.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
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
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [title, setTitle] = useState(place.title);
  const [city, setCity] = useState(place.city);
  const [country, setCountry] = useState(place.country);
  const [category, setCategory] = useState<Category>(place.category);
  const [description, setDescription] = useState(place.description);
  const [aestheticNote, setAestheticNote] = useState(place.aestheticNote);
  const [tagsText, setTagsText] = useState(place.tags.join(", "));

  useEffect(() => {
    setEditing(false);
    setTitle(place.title);
    setCity(place.city);
    setCountry(place.country);
    setCategory(place.category);
    setDescription(place.description);
    setAestheticNote(place.aestheticNote);
    setTagsText(place.tags.join(", "));
  }, [place]);

  async function handleSave() {
    const tags = tagsText
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      const updated = await updatePlace.mutateAsync({
        placeId: place.id,
        body: { title, city, country, category, description, aestheticNote, tags },
      });
      onChange(updated);
      setEditing(false);
      toast.success("Place updated");
    } catch {
      toast.error("Failed to update place");
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
        className="fixed inset-0 z-50 flex justify-end bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      >
        <div
          className="h-full w-full max-w-md overflow-y-auto bg-background shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="absolute right-3 top-3 z-10 flex gap-1.5">
            {!editing && (
              <>
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="rounded-full bg-background/90 p-1.5 shadow-md hover:bg-muted"
                  title="Edit place"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(true)}
                  className="rounded-full bg-background/90 p-1.5 shadow-md hover:bg-destructive/10 hover:text-destructive"
                  title="Delete place"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </>
            )}
            <button
              type="button"
              onClick={onClose}
              className="rounded-full bg-background/90 p-1.5 shadow-md"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <img
            src={resolveImageUrl(place.image)}
            alt={place.title}
            className="h-72 w-full object-cover"
          />
          <div className="space-y-4 p-6">
            {editing ? (
              <>
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
                  <Field label="Tags (comma-separated)">
                    <Input value={tagsText} onChange={(e) => setTagsText(e.target.value)} />
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
                  <Button className="flex-1" onClick={handleSave} disabled={updatePlace.isPending}>
                    {updatePlace.isPending ? "Saving…" : "Save changes"}
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div>
                  <h2 className="font-serif text-3xl tracking-tight">{place.title}</h2>
                  <div className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                    <MapPin className="h-3.5 w-3.5" /> {place.city}, {place.country}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <CategoryBadge category={place.category} />
                  <SourceBadge source={place.source} />
                  <VerificationBadge status={place.verification} />
                  <ConfidenceBadge value={place.confidence} />
                </div>
                <div>
                  <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    Extracted description
                  </div>
                  <p className="mt-1 text-sm leading-relaxed">{place.description}</p>
                </div>
                <div className="rounded-xl bg-muted/60 p-3">
                  <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    Aesthetic note
                  </div>
                  <p className="mt-1 font-serif text-base italic">&ldquo;{place.aestheticNote}&rdquo;</p>
                </div>
                <div>
                  <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    Why it was saved
                  </div>
                  <p className="mt-1 text-sm text-foreground/80">{place.reason}</p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {place.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-md bg-muted px-2 py-1 text-[11px] text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </>
            )}
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
