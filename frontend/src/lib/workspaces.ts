import type { Workspace } from "@/lib/types";

export type WorkspaceGroup = {
  country: string;
  flag: string;
  workspaces: Workspace[];
};

export function groupWorkspacesByCountry(workspaces: Workspace[]): WorkspaceGroup[] {
  const map = new Map<string, WorkspaceGroup>();

  for (const ws of workspaces) {
    const country = ws.country || ws.destination.split(",").pop()?.trim() || "Other";
    const existing = map.get(country);
    if (existing) {
      existing.workspaces.push(ws);
    } else {
      map.set(country, { country, flag: ws.flag, workspaces: [ws] });
    }
  }

  return Array.from(map.values())
    .map((group) => ({
      ...group,
      workspaces: [...group.workspaces].sort((a, b) => a.city.localeCompare(b.city)),
    }))
    .sort((a, b) => a.country.localeCompare(b.country));
}
