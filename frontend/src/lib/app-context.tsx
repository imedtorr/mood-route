import { createContext, useContext, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { workspaces as defaultWorkspaces, type Workspace } from "@/lib/mock-data";
import { useSyncPlacesOnUploadComplete, useWorkspaces } from "@/lib/api/hooks";

type Ctx = {
  workspace: Workspace;
  setWorkspace: (w: Workspace) => void;
  aesthetic: boolean;
  setAesthetic: (b: boolean) => void;
  agentOpen: boolean;
  setAgentOpen: (b: boolean) => void;
};

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data: wsList } = useWorkspaces();
  const list = wsList?.length ? wsList : defaultWorkspaces;
  const [workspace, setWorkspaceState] = useState<Workspace>(list[0]);
  const [aesthetic, setAesthetic] = useState(false);
  const [agentOpen, setAgentOpen] = useState(true);

  const setWorkspace = (w: Workspace) => {
    setWorkspaceState(w);
    qc.invalidateQueries();
  };

  const active = list.find((w) => w.id === workspace.id) ?? list[0];

  return (
    <AppCtx.Provider
      value={{
        workspace: active,
        setWorkspace,
        aesthetic,
        setAesthetic,
        agentOpen,
        setAgentOpen,
      }}
    >
      <UploadPlacesSync />
      <div className={aesthetic ? "aesthetic" : ""}>{children}</div>
    </AppCtx.Provider>
  );
}

function UploadPlacesSync() {
  useSyncPlacesOnUploadComplete();
  return null;
}

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
