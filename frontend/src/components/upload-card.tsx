import { Clock, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { SourceBadge } from "@/components/badges";
import { Progress } from "@/components/ui/progress";
import { resolveImageUrl } from "@/lib/api/client";
import type { Upload, UploadStatus } from "@/lib/types";

const statusMeta: Record<
  UploadStatus,
  { className: string; icon: "spin" | "done" | "warn" | "wait" }
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
};

export function UploadCard({ upload }: { upload: Upload }) {
  const meta = statusMeta[upload.status];
  const label =
    upload.status === "Fallback / Needs manual review" ? "Needs manual review" : upload.status;

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card transition-shadow hover:shadow-md">
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
            <SourceBadge source={upload.source} className="shrink-0" />
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
              )}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
