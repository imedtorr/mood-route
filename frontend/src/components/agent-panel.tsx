import { useState } from "react";
import { useAgentEvents } from "@/lib/api/hooks";
import { useApp } from "@/lib/app-context";
import type { AgentStatus } from "@/lib/types";
import { AgentBadge, agentStyles } from "@/components/badges";
import { ChevronDown, Wrench, ArrowRight, Workflow, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const statusStyles: Record<AgentStatus, string> = {
  Success: "bg-success/12 text-success border-success/25",
  Fallback: "bg-warning/15 text-warning-foreground border-warning/35",
  "Needs Review": "bg-destructive/10 text-destructive border-destructive/25",
};

function confidenceTier(score: number) {
  if (score >= 0.85) return "bg-success/12 text-success border-success/25";
  if (score >= 0.65) return "bg-warning/15 text-warning-foreground border-warning/35";
  return "bg-destructive/10 text-destructive border-destructive/25";
}

export function AgentPanel() {
  const { agentOpen, setAgentOpen, workspace } = useApp();
  const { data: agentTimeline = [] } = useAgentEvents();
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <>
      {agentOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-foreground/20 backdrop-blur-sm lg:hidden"
          onClick={() => setAgentOpen(false)}
          aria-label="Close agent activity"
        />
      )}

      <aside
        className={cn(
          "shrink-0 border-l border-border bg-card transition-all duration-300",
          "max-lg:fixed max-lg:inset-y-0 max-lg:right-0 max-lg:z-40 max-lg:w-[88vw] max-lg:max-w-sm max-lg:shadow-xl",
          agentOpen
            ? "w-80 translate-x-0"
            : "w-0 overflow-hidden border-l-0 max-lg:translate-x-full",
        )}
      >
        <div className="flex h-full w-80 max-w-full flex-col">
          <div className="flex items-start justify-between gap-2 border-b border-border px-5 py-4">
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Workflow className="size-4" />
              </span>
              <div>
                <h2 className="font-serif text-base font-semibold leading-tight">Agent Activity</h2>
                <p className="text-xs text-muted-foreground">Explainable AI workflow</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 shrink-0"
              onClick={() => setAgentOpen(false)}
              aria-label="Close panel"
            >
              <X className="size-4" />
            </Button>
          </div>

          <div className="border-b border-border bg-muted/40 px-5 py-2.5">
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {workspace.flag} {workspace.name}
              </span>{" "}
              · live workflow
            </p>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            {agentTimeline.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No agent activity yet. Add inspiration or generate a trip.
              </p>
            )}
            {agentTimeline.map((step, i) => {
              const isOpen = expanded === step.id;
              const isLast = i === agentTimeline.length - 1;
              return (
                <div key={step.id} className="relative pl-7">
                  <span
                    className={cn(
                      "absolute left-[7px] top-1.5 size-2.5 rounded-full ring-4 ring-card",
                      agentStyles[step.agent].dot,
                    )}
                  />
                  {!isLast && (
                    <span className="absolute left-[11px] top-5 h-[calc(100%-0.5rem)] w-px bg-border" />
                  )}

                  <div className="pb-5">
                    <div className="flex items-center justify-between gap-2">
                      <AgentBadge agent={step.agent} />
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {step.time}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm font-medium text-foreground text-pretty">
                      {step.summary}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                          statusStyles[step.status],
                        )}
                      >
                        {step.status}
                      </span>
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium tabular-nums",
                          confidenceTier(step.confidence),
                        )}
                      >
                        {Math.round(step.confidence * 100)}%
                      </span>
                      <button
                        type="button"
                        onClick={() => setExpanded(isOpen ? null : step.id)}
                        className="ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                      >
                        Details
                        <ChevronDown
                          className={cn("size-3 transition-transform", isOpen && "rotate-180")}
                        />
                      </button>
                    </div>
                    {isOpen && (
                      <div className="mt-2.5 space-y-2.5 rounded-lg border border-border bg-muted/40 p-3 text-xs">
                        <div>
                          <p className="mb-1 font-medium text-muted-foreground">Tool calls</p>
                          <div className="flex flex-wrap gap-1.5">
                            {step.tools.map((t) => (
                              <span
                                key={t}
                                className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-1.5 py-0.5 font-mono text-[11px]"
                              >
                                <Wrench className="size-3 text-muted-foreground" />
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="space-y-1.5">
                          <div>
                            <span className="text-muted-foreground">Input · </span>
                            <span className="font-mono text-[11px]">{step.input}</span>
                          </div>
                          <div className="flex items-start gap-1">
                            <ArrowRight className="mt-0.5 size-3 shrink-0 text-muted-foreground" />
                            <span className="font-mono text-[11px]">{step.output}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </aside>
    </>
  );
}
