import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import {
  ArrowRightLeft,
  ExternalLink,
  MoreHorizontal,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { CategoryBadge } from "@/components/badges";
import { useItineraryStopAction, usePlaces } from "@/lib/api/hooks";
import { resolveImageUrl } from "@/lib/api/client";
import { useApp } from "@/lib/app-context";
import { cn } from "@/lib/utils";
import type { ItineraryDay, ItineraryStop, Place } from "@/lib/types";

type StopActionsMenuProps = {
  stop: ItineraryStop;
  dayNumber: number;
  days: ItineraryDay[];
  onMovedToDay?: (dayNumber: number) => void;
};

function filterPlacesByCity(places: Place[], city: string) {
  const normalized = city.trim().toLowerCase();
  if (!normalized) return places;
  return places.filter((p) => p.city.trim().toLowerCase() === normalized);
}

function filterPlacesByQuery(places: Place[], query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return places;
  return places.filter(
    (p) =>
      p.title.toLowerCase().includes(q) ||
      (p.district?.toLowerCase().includes(q) ?? false) ||
      p.tags.some((t) => t.toLowerCase().includes(q)),
  );
}

export function StopActionsMenu({ stop, dayNumber, days, onMovedToDay }: StopActionsMenuProps) {
  const navigate = useNavigate();
  const { workspace } = useApp();
  const stopAction = useItineraryStopAction();
  const { data: allPlaces = [], isLoading: placesLoading } = usePlaces();
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [search, setSearch] = useState("");

  const replaceOptions = useMemo(() => {
    const inCity = filterPlacesByCity(allPlaces, workspace.city);
    const filtered = filterPlacesByQuery(inCity, search);
    return [...filtered].sort((a, b) => a.title.localeCompare(b.title));
  }, [allPlaces, workspace.city, search]);

  const busy = stopAction.isPending;
  const otherDays = days.filter((d) => d.day !== dayNumber);

  async function runAction(
    body: Parameters<typeof stopAction.mutateAsync>[0],
    successMessage: string,
    onSuccess?: () => void,
  ) {
    try {
      await stopAction.mutateAsync(body);
      toast.success(successMessage);
      onSuccess?.();
    } catch {
      toast.error("Could not update the route");
    }
  }

  function openPlace() {
    if (!stop.placeId) {
      toast.error("This stop is not linked to a saved place");
      return;
    }
    navigate({ to: "/places", search: { placeId: stop.placeId } });
  }

  async function confirmRemoveStop() {
    await runAction(
      { action: "remove", day: dayNumber, stopN: stop.n },
      "Stop removed from route",
    );
    setConfirmRemove(false);
  }

  async function moveToDay(targetDay: number) {
    await runAction(
      { action: "move", day: dayNumber, stopN: stop.n, targetDay },
      `Moved to Day ${targetDay}`,
      () => onMovedToDay?.(targetDay),
    );
  }

  async function replaceWith(placeId: string) {
    await runAction(
      { action: "replace", day: dayNumber, stopN: stop.n, placeId },
      "Stop replaced",
      () => {
        setReplaceOpen(false);
        setSearch("");
      },
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            disabled={busy}
            className={cn(
              "rounded-full p-1.5 text-muted-foreground shadow-sm ring-1 ring-border/60 transition",
              "hover:bg-muted hover:text-foreground disabled:opacity-50",
            )}
            aria-label="More options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          side="right"
          align="start"
          sideOffset={8}
          alignOffset={-4}
          collisionPadding={12}
          className="w-56 rounded-xl border-border/70 p-1.5 shadow-[var(--shadow-card)]"
        >
          <DropdownMenuItem
            onClick={openPlace}
            disabled={!stop.placeId}
            className="rounded-lg"
          >
            <ExternalLink className="h-4 w-4" />
            Open place
          </DropdownMenuItem>

          {otherDays.length > 0 && (
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className="rounded-lg">
                <ArrowRightLeft className="h-4 w-4" />
                Move to day
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className="w-52 rounded-xl border-border/70 p-1.5 shadow-[var(--shadow-card)]">
                {otherDays.map((d) => (
                  <DropdownMenuItem
                    key={d.day}
                    onClick={() => moveToDay(d.day)}
                    className="flex-col items-start gap-0.5 rounded-lg py-2"
                  >
                    <span className="font-serif text-base leading-none">Day {d.day}</span>
                    {d.theme ? (
                      <span className="line-clamp-2 text-[11px] leading-snug italic text-muted-foreground">
                        {d.theme}
                      </span>
                    ) : null}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          )}

          <DropdownMenuItem onClick={() => setReplaceOpen(true)} className="rounded-lg">
            <Search className="h-4 w-4" />
            Replace place…
          </DropdownMenuItem>

          <DropdownMenuItem disabled className="rounded-lg">
            <Sparkles className="h-4 w-4 text-primary/70" />
            Suggest alternative
            <DropdownMenuShortcut className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] tracking-normal">
              Soon
            </DropdownMenuShortcut>
          </DropdownMenuItem>

          <DropdownMenuSeparator className="bg-border/70" />

          <DropdownMenuItem
            className="rounded-lg text-destructive focus:bg-destructive/10 focus:text-destructive"
            onClick={() => setConfirmRemove(true)}
          >
            <Trash2 className="h-4 w-4" />
            Remove from route
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={confirmRemove} onOpenChange={setConfirmRemove}>
        <AlertDialogContent className="rounded-2xl border-border/70 shadow-[var(--shadow-card)]">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-serif text-xl">Remove from route?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{stop.title}&rdquo; will be removed from Day {dayNumber}. The place stays in
              your Places catalog.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-xl">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmRemoveStop}
              className="rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog
        open={replaceOpen}
        onOpenChange={(open) => {
          setReplaceOpen(open);
          if (!open) setSearch("");
        }}
      >
        <DialogContent className="max-h-[85vh] gap-0 overflow-hidden rounded-2xl border-border/70 p-0 shadow-[var(--shadow-card)] sm:max-w-md">
          <DialogHeader className="space-y-1 border-b border-border/70 px-6 py-5 text-left">
            <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
              Replace stop
            </p>
            <DialogTitle className="font-serif text-2xl leading-tight">
              {stop.title}
            </DialogTitle>
            <DialogDescription>
              {workspace.city
                ? `Saved places in ${workspace.city}`
                : "Pick another place from your workspace"}
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 py-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={workspace.city ? `Filter places in ${workspace.city}…` : "Filter places…"}
                autoFocus
                className="rounded-xl border-border/70 bg-card pl-9 shadow-sm"
              />
            </div>
          </div>

          <div className="max-h-72 space-y-1.5 overflow-y-auto px-4 pb-5">
            {placesLoading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Loading places…</p>
            ) : replaceOptions.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {search.trim()
                  ? "No places match your search"
                  : workspace.city
                    ? `No saved places in ${workspace.city}`
                    : "No saved places yet"}
              </p>
            ) : (
              replaceOptions.map((place) => (
                <button
                  key={place.id}
                  type="button"
                  disabled={busy || place.id === stop.placeId}
                  onClick={() => replaceWith(place.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl border border-border/60 bg-card p-2.5 text-left shadow-sm transition",
                    "hover:-translate-y-px hover:shadow-md disabled:opacity-50",
                  )}
                >
                  <img
                    src={resolveImageUrl(place.image)}
                    alt=""
                    className="h-12 w-12 shrink-0 rounded-lg object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium leading-tight">{place.title}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {place.city}
                      {place.district ? ` · ${place.district}` : ""}
                    </div>
                  </div>
                  <CategoryBadge category={place.category} />
                </button>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
