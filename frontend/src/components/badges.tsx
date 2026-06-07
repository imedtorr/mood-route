import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Search,
  BookmarkCheck,
} from "lucide-react";
import type { Verification, SourceType, AgentName } from "@/lib/mock-data";

export const agentStyles: Record<AgentName, { dot: string; badge: string }> = {
  "Supervisor Agent": {
    dot: "bg-agent-supervisor",
    badge: "bg-agent-supervisor/12 text-agent-supervisor border-agent-supervisor/25",
  },
  "Curator Agent": {
    dot: "bg-agent-curator",
    badge: "bg-agent-curator/12 text-agent-curator border-agent-curator/25",
  },
  "Researcher Agent": {
    dot: "bg-agent-researcher",
    badge: "bg-agent-researcher/12 text-agent-researcher border-agent-researcher/25",
  },
  "Planner Agent": {
    dot: "bg-agent-planner",
    badge: "bg-agent-planner/12 text-agent-planner border-agent-planner/25",
  },
  "Verifier Agent": {
    dot: "bg-agent-verifier",
    badge: "bg-agent-verifier/15 text-warning-foreground border-agent-verifier/35",
  },
};

export function AgentBadge({ agent, className }: { agent: AgentName; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
        agentStyles[agent].badge,
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", agentStyles[agent].dot)} />
      {agent}
    </span>
  );
}

export function VerificationBadge({
  status,
  className,
}: {
  status: Verification;
  className?: string;
}) {
  const map = {
    Verified: { cls: "bg-success/12 text-success border-success/25", Icon: CheckCircle2 },
    Unverified: { cls: "bg-muted text-muted-foreground border-border", Icon: HelpCircle },
    "Needs Recheck": {
      cls: "bg-warning/15 text-warning-foreground border-warning/35",
      Icon: AlertCircle,
    },
  } as const;
  const { cls, Icon } = map[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
        cls,
        className,
      )}
    >
      <Icon className="h-3 w-3" /> {status}
    </span>
  );
}

export function SourceBadge({
  source,
  className,
}: {
  source: SourceType | "Saved" | "RAG Similar" | "Verified Recommendation";
  className?: string;
}) {
  const map: Record<string, { cls: string; Icon: typeof CheckCircle2 }> = {
    Pinterest: {
      cls: "bg-destructive/10 text-destructive border-destructive/20",
      Icon: BookmarkCheck,
    },
    Instagram: {
      cls: "bg-agent-planner/10 text-agent-planner border-agent-planner/20",
      Icon: Sparkles,
    },
    Screenshot: { cls: "bg-muted text-muted-foreground border-border", Icon: Search },
    Article: { cls: "bg-info/10 text-info border-info/25", Icon: BookmarkCheck },
    Saved: { cls: "bg-primary/10 text-primary border-primary/20", Icon: BookmarkCheck },
    "RAG Similar": {
      cls: "bg-agent-planner/10 text-agent-planner border-agent-planner/25",
      Icon: Sparkles,
    },
    "Verified Recommendation": { cls: "bg-info/10 text-info border-info/25", Icon: CheckCircle2 },
  };
  const { cls, Icon } = map[source];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
        cls,
        className,
      )}
    >
      <Icon className="h-3 w-3" /> {source}
    </span>
  );
}

export function ConfidenceBadge({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value * 100);
  const tier = value >= 0.85 ? "high" : value >= 0.65 ? "medium" : "low";
  const tierStyles = {
    high: "bg-success/12 text-success border-success/25",
    medium: "bg-warning/15 text-warning-foreground border-warning/35",
    low: "bg-destructive/10 text-destructive border-destructive/25",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium tabular-nums",
        tierStyles[tier],
        className,
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          tier === "high" ? "bg-success" : tier === "medium" ? "bg-warning" : "bg-destructive",
        )}
      />
      {pct}%
    </span>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-accent/60 px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
      {category}
    </span>
  );
}
