import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { useReviewAction, useReviewQueue } from "@/lib/api/hooks";
import { resolveImageUrl } from "@/lib/api/client";
import type { ReviewCard } from "@/lib/types";
import { SourceBadge, CategoryBadge } from "@/components/badges";
import { Check, Pencil, GitMerge, X as XIcon, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/review")({
  head: () => ({ meta: [{ title: "Review Queue — MoodRoute" }] }),
  component: ReviewPage,
});

function confTone(v: number) {
  if (v >= 0.85) return "bg-success/12 text-success border-success/25";
  if (v >= 0.65) return "bg-warning/15 text-warning-foreground border-warning/35";
  return "bg-destructive/10 text-destructive border-destructive/25";
}

function ReviewPage() {
  const { data: reviewQueue = [] } = useReviewQueue();
  const reviewAction = useReviewAction();
  const [editItem, setEditItem] = useState<ReviewCard | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editCity, setEditCity] = useState("");

  async function act(reviewId: string, action: string, extra?: Record<string, unknown>) {
    try {
      await reviewAction.mutateAsync({ reviewId, action, ...extra });
      toast.success(`Review ${action}ed`);
    } catch {
      toast.error("Action failed");
    }
  }

  async function submitEdit() {
    if (!editItem) return;
    await act(editItem.id, "edit", {
      edits: { title: editTitle, city: editCity.replace("?", "") },
    });
    setEditItem(null);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Human-in-the-loop"
        title="Review Queue"
        description="The Verifier Agent surfaces uncertain or conflicting extractions. A few seconds of your judgment keeps the workspace clean."
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs">
            <ShieldCheck className="h-3.5 w-3.5 text-success" /> {reviewQueue.length} items waiting
          </span>
        }
      />

      <div className="grid gap-4 px-8 py-8 lg:grid-cols-2">
        {reviewQueue.map((r) => (
          <article
            key={r.id}
            className="overflow-hidden rounded-2xl border border-border bg-card shadow-[var(--shadow-card)]"
          >
            <div className="grid sm:grid-cols-[140px_1fr]">
              <img src={resolveImageUrl(r.image)} alt="" className="h-full w-full object-cover sm:h-full" />
              <div className="space-y-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                      {r.type}
                    </div>
                    <h3 className="mt-1 font-serif text-xl leading-tight">{r.title}</h3>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {r.city}, {r.country}
                    </div>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-mono font-medium",
                      confTone(r.confidence),
                    )}
                  >
                    {Math.round(r.confidence * 100)}%
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <CategoryBadge category={r.category} />
                  <SourceBadge source={r.source} />
                </div>
                <p className="rounded-lg bg-muted/60 p-2.5 text-xs text-foreground/80">
                  <span className="font-medium text-foreground">AI explanation · </span>
                  {r.explanation}
                </p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <ActionBtn
                    icon={Check}
                    label="Confirm"
                    primary={r.suggestedAction === "Confirm"}
                    onClick={() => act(r.id, "confirm")}
                  />
                  <ActionBtn
                    icon={Pencil}
                    label="Edit"
                    primary={r.suggestedAction === "Edit"}
                    onClick={() => {
                      setEditItem(r);
                      setEditTitle(r.title);
                      setEditCity(r.city);
                    }}
                  />
                  <ActionBtn
                    icon={GitMerge}
                    label="Merge Duplicate"
                    primary={r.suggestedAction === "Merge Duplicate"}
                    onClick={() =>
                      act(r.id, "merge", {
                        mergeIntoPlaceId: r.placeIds?.[0],
                      })
                    }
                  />
                  <ActionBtn icon={XIcon} label="Reject" onClick={() => act(r.id, "reject")} />
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>

      <Dialog open={!!editItem} onOpenChange={(o) => !o && setEditItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit place</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              placeholder="Place name"
            />
            <Input
              value={editCity}
              onChange={(e) => setEditCity(e.target.value)}
              placeholder="City"
            />
            <Button onClick={submitEdit} className="w-full">
              Save & confirm
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ActionBtn({
  icon: Icon,
  label,
  primary,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  primary?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition",
        primary
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-background hover:bg-muted",
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </button>
  );
}
