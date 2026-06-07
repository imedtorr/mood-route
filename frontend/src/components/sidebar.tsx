import { Link, useRouterState } from "@tanstack/react-router";
import {
  Inbox,
  MapPin,
  Hammer,
  Route,
  ClipboardCheck,
  Plus,
  ChevronsUpDown,
  Compass,
  PanelRightOpen,
  Check,
} from "lucide-react";
import { useState } from "react";
import { useApp } from "@/lib/app-context";
import { useWorkspaces } from "@/lib/api/hooks";
import { workspaces as fallbackWorkspaces } from "@/lib/mock-data";
import { groupWorkspacesByCountry } from "@/lib/workspaces";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { NewWorkspaceDialog } from "@/components/new-workspace-dialog";

const nav = [
  { to: "/", label: "Inbox", icon: Inbox },
  { to: "/places", label: "Places", icon: MapPin },
  { to: "/trip-builder", label: "Trip Builder", icon: Hammer },
  { to: "/route-planner", label: "Route Planner", icon: Route },
  { to: "/review", label: "Review Queue", icon: ClipboardCheck },
] as const;

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const { workspace, setWorkspace, agentOpen, setAgentOpen } = useApp();
  const { data: wsList } = useWorkspaces();
  const workspaces = wsList?.length ? wsList : fallbackWorkspaces;
  const groups = groupWorkspacesByCountry(workspaces);
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <>
      <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex">
        <div className="flex items-center gap-2 px-5 py-5">
          <span className="flex size-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Compass className="size-4" />
          </span>
          <span className="font-serif text-xl font-semibold tracking-tight text-sidebar-foreground">
            MoodRoute
          </span>
        </div>

        <div className="relative px-3 pb-2">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="flex w-full items-center gap-2.5 rounded-xl border border-sidebar-border bg-card px-3 py-2.5 text-left transition-colors hover:bg-sidebar-accent"
          >
            <span className="text-lg leading-none">{workspace.flag}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-sidebar-foreground">
                {workspace.name}
              </span>
              <span className="block truncate text-xs text-muted-foreground">
                {workspace.destination}
              </span>
            </span>
            <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" />
          </button>
          {open && (
            <div className="absolute left-3 right-3 z-20 mt-1 max-h-80 overflow-y-auto rounded-xl border border-border bg-popover shadow-lg">
              {groups.map((group) => (
                <div key={group.country}>
                  <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 text-xs font-medium text-muted-foreground">
                    <span>{group.flag}</span>
                    <span>{group.country}</span>
                  </div>
                  {group.workspaces.map((w) => (
                    <button
                      key={w.id}
                      type="button"
                      onClick={() => {
                        setWorkspace(w);
                        setOpen(false);
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-muted"
                    >
                      <span className="min-w-0 flex-1 text-left">
                        <span className="block truncate font-medium">{w.city}</span>
                        <span className="block truncate text-xs text-muted-foreground">{w.name}</span>
                      </span>
                      {w.id === workspace.id && <Check className="size-4 shrink-0 text-primary" />}
                    </button>
                  ))}
                </div>
              ))}
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setCreateOpen(true);
                }}
                className="flex w-full items-center gap-2 border-t border-border px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
              >
                <Plus className="size-4" /> New Workspace
              </button>
            </div>
          )}
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
          {nav.map((item) => {
            const active = item.to === "/" ? path === "/" : path.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <Button
            variant={agentOpen ? "secondary" : "outline"}
            className="w-full justify-start gap-2"
            onClick={() => setAgentOpen(!agentOpen)}
          >
            <PanelRightOpen className="size-4" />
            Agent Activity
          </Button>
        </div>
      </aside>

      <NewWorkspaceDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
