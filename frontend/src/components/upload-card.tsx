import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Clock, Loader2, CheckCircle2, AlertTriangle, Square, Trash2, Ban } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { SourceBadge } from "@/components/badges";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
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
import { resolveImageUrl } from "@/lib/api/client";
import {
  PROCESSED_UPLOAD_STATUSES,
  useCancelUpload,
  useDeleteUpload,
} from "@/lib/api/hooks";
import type { Upload, UploadStatus } from "@/lib/types";

const RUNNING_STATUSES: UploadStatus[] = [
  "Parsing link",
  "OCR processing",
  "Extracting places",
  "Enriching details",
  "Classifying categories",
];

const statusMeta: Record<
  UploadStatus,
  { className: string; icon: "spin" | "done" | "warn" | "wait" | "cancel" }
> = {
  "Parsing link": { className: "bg-info/12 text-info border-info/25", icon: "spin" },
  "OCR processing": { className: "bg-info/12 text-info border-info/25", icon: "spin" },
  "Extracting places": { className: "bg-info/12 text-info border-info/25", icon: "spin" },
  "Enriching details": { className: "bg-info/12 text-info border-info/25", icon: "spin" },
  "Classifying categories": { className: "bg-info/12 text-info border-info/25", icon: "spin" },
  "Awaiting review": {
    className: "bg-warning/15 text-warning-foreground border-warning/35",
    icon: "wait",
  },
  Completed: { className: "bg-success/12 text-success border-success/25", icon: "done" },
  "Fallback / Needs manual review": {
    className: "bg-destructive/10 text-destructive border-destructive/25",
    icon: "warn",
  },
  Cancelled: {
    className: "bg-muted text-muted-foreground border-border",
    icon: "cancel",
  },
};

export function UploadCard({ upload }: { upload: Upload }) {
  const navigate = useNavigate();
  const cancelUpload = useCancelUpload();
  const deleteUpload = useDeleteUpload();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const meta = statusMeta[upload.status];
  const label =
    upload.status === "Fallback / Needs manual review" ? "Needs manual review" : upload.status;
  const isRunning = RUNNING_STATUSES.includes(upload.status);
  const isProcessed = PROCESSED_UPLOAD_STATUSES.includes(upload.status);
  const placeId = upload.placeIds?.[0];
  const isClickable = isProcessed && !!placeId;

  async function handleStop(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await cancelUpload.mutateAsync(upload.id);
      toast.success("Processing stopped");
    } catch {
      toast.error("Could not stop processing");
    }
  }

  async function handleDelete() {
    try {
      await deleteUpload.mutateAsync(upload.id);
      toast.success("Upload removed");
      setConfirmDelete(false);
    } catch {
      toast.error("Could not delete upload");
    }
  }

  function handleCardClick() {
    if (!isClickable || !placeId) return;
    navigate({ to: "/places", search: { placeId } });
  }

  return (
    <>
      <div
        role={isClickable ? "button" : undefined}
        tabIndex={isClickable ? 0 : undefined}
        onClick={handleCardClick}
        onKeyDown={(e) => {
          if (isClickable && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            handleCardClick();
          }
        }}
        className={cn(
          "group overflow-hidden rounded-2xl border border-border bg-card transition-shadow",
          isClickable && "cursor-pointer hover:border-primary/40 hover:shadow-md",
          !isClickable && "hover:shadow-md",
        )}
      >
        <div className="flex gap-4 p-4">
          <div className="size-20 shrink-0 overflow-hidden rounded-xl bg-muted">
            <img
              src={resolveImageUrl(upload.image)}
              alt={upload.title}
              className="size-full object-cover"
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <p className="truncate text-sm font-medium text-foreground">{upload.title}</p>
              <div className="flex shrink-0 items-center gap-1">
                <SourceBadge source={upload.source} />
                {isRunning && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-foreground"
                    title="Stop processing"
                    disabled={cancelUpload.isPending}
                    onClick={handleStop}
                  >
                    <Square className="size-3.5 fill-current" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7 text-muted-foreground hover:text-destructive"
                  title="Delete upload"
                  disabled={deleteUpload.isPending}
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmDelete(true);
                  }}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            </div>

            {upload.note && (
              <p className="mt-1 line-clamp-1 text-xs italic text-muted-foreground">
                &ldquo;{upload.note}&rdquo;
              </p>
            )}

            <div className="mt-2 flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
                  meta.className,
                )}
              >
                {meta.icon === "spin" && <Loader2 className="size-3 animate-spin" />}
                {meta.icon === "done" && <CheckCircle2 className="size-3" />}
                {meta.icon === "warn" && <AlertTriangle className="size-3" />}
                {meta.icon === "wait" && <Clock className="size-3" />}
                {meta.icon === "cancel" && <Ban className="size-3" />}
                {label}
              </span>
              <span className="ml-auto inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Clock className="size-3" />
                {upload.time}
              </span>
            </div>

            <div className="mt-2.5">
              <Progress
                value={upload.progress}
                className={cn(
                  "h-1.5",
                  upload.status === "Fallback / Needs manual review" && "[&>div]:bg-destructive",
                  upload.status === "Cancelled" && "[&>div]:bg-muted-foreground/40",
                )}
              />
            </div>

            {isClickable && (
              <p className="mt-2 text-[11px] text-primary opacity-0 transition-opacity group-hover:opacity-100">
                View in Places →
              </p>
            )}
          </div>
        </div>
      </div>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent onClick={(e) => e.stopPropagation()}>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this upload?</AlertDialogTitle>
            <AlertDialogDescription>
              {isRunning
                ? "Processing will be stopped and this upload will be removed from your inbox."
                : "This removes the upload from your inbox. Places already saved will stay in the Places tab."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
