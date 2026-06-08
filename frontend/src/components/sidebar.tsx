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
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useApp, latestWorkspace } from "@/lib/app-context";
import { useDeleteWorkspace, useWorkspaces } from "@/lib/api/hooks";
import { workspaces as fallbackWorkspaces } from "@/lib/mock-data";
import type { Workspace } from "@/lib/types";
import { groupWorkspacesByCountry } from "@/lib/workspaces";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { NewWorkspaceDialog } from "@/components/new-workspace-dialog";
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

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

const nav = [
  { to: "/", label: "Inbox", icon: Inbox },
  { to: "/places", label: "Places", icon: MapPin },
  { to: "/trip-builder", label: "Trip Builder", icon: Hammer },
  { to: "/route-planner", label: "Route Planner", icon: Route },
  { to: "/review", label: "Review Queue", icon: ClipboardCheck },
] as const;

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const { workspace, setWorkspace, clearWorkspaceSelection, agentOpen, setAgentOpen } = useApp();
  const { data: wsList } = useWorkspaces();
  const deleteWorkspace = useDeleteWorkspace();
  const workspaces = wsList?.length ? wsList : USE_MOCK ? fallbackWorkspaces : [];
  const groups = groupWorkspacesByCountry(workspaces);
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Workspace | null>(null);

  async function handleDelete() {
    if (!pendingDelete) return;
    const deletedId = pendingDelete.id;
    try {
      await deleteWorkspace.mutateAsync(deletedId);
      const remaining = workspaces.filter((w) => w.id !== deletedId);
      if (deletedId === workspace.id) {
        if (remaining.length) {
          setWorkspace(latestWorkspace(remaining));
        } else {
          clearWorkspaceSelection();
        }
      }
      toast.success(`Trip to ${pendingDelete.city} removed`);
      setPendingDelete(null);
    } catch {
      toast.error("Could not delete trip");
    }
  }

  return (
    <>
      <aside className="hidden h-svh w-64 shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar md:flex">
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
              {groups.length === 0 && (
                <p className="px-3 py-2 text-sm text-muted-foreground">No trips yet</p>
              )}
              {groups.map((group) => (
                <div key={group.country}>
                  <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 text-xs font-medium text-muted-foreground">
                    <span>{group.flag}</span>
                    <span>{group.country}</span>
                  </div>
                  {group.workspaces.map((w) => (
                    <div
                      key={w.id}
                      className="group flex w-full items-center hover:bg-muted"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setWorkspace(w);
                          setOpen(false);
                        }}
                        className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-sm"
                      >
                        <span className="min-w-0 flex-1 text-left">
                          <span className="block truncate font-medium">{w.city}</span>
                          <span className="block truncate text-xs text-muted-foreground">{w.name}</span>
                        </span>
                        {w.id === workspace.id && (
                          <Check className="size-4 shrink-0 text-primary" />
                        )}
                      </button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="mr-1 size-7 shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                        title="Delete trip"
                        disabled={deleteWorkspace.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          setPendingDelete(w);
                        }}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
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

      <AlertDialog open={!!pendingDelete} onOpenChange={(v) => !v && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this trip?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete && (
                <>
                  Remove <strong>{pendingDelete.city}</strong> ({pendingDelete.name})? All places,
                  uploads, and routes will be permanently deleted.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
              disabled={deleteWorkspace.isPending}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
