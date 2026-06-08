import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { workspaces as defaultWorkspaces, type Workspace } from "@/lib/mock-data";
import { useSyncPlacesOnUploadComplete, useWorkspaces } from "@/lib/api/hooks";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export const EMPTY_WORKSPACE: Workspace = {
  id: "",
  name: "No trip",
  flag: "🌍",
  country: "",
  city: "",
  destination: "Create a workspace to get started",
};

export function latestWorkspace(list: Workspace[]): Workspace {
  return [...list].sort((a, b) => {
    const ta = a.updatedAt ? Date.parse(a.updatedAt) : 0;
    const tb = b.updatedAt ? Date.parse(b.updatedAt) : 0;
    return tb - ta;
  })[0];
}

type Ctx = {
  workspace: Workspace;
  setWorkspace: (w: Workspace) => void;
  clearWorkspaceSelection: () => void;
  aesthetic: boolean;
  setAesthetic: (b: boolean) => void;
  agentOpen: boolean;
  setAgentOpen: (b: boolean) => void;
};

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data: wsList, isSuccess } = useWorkspaces();
  const list = wsList?.length ? wsList : USE_MOCK ? defaultWorkspaces : [];
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const userPicked = useRef(false);
  const [aesthetic, setAesthetic] = useState(false);
  const [agentOpen, setAgentOpen] = useState(true);

  useEffect(() => {
    if (!isSuccess || wsList === undefined) return;
    if (!workspaceId) {
      if (wsList.length && !userPicked.current) {
        setWorkspaceId(latestWorkspace(wsList).id);
      }
      return;
    }
    if (!wsList.some((w) => w.id === workspaceId)) {
      setWorkspaceId(wsList.length ? latestWorkspace(wsList).id : null);
      qc.invalidateQueries();
    }
  }, [isSuccess, wsList, workspaceId, qc]);

  const setWorkspace = (w: Workspace) => {
    userPicked.current = true;
    setWorkspaceId(w.id);
    qc.invalidateQueries();
  };

  const clearWorkspaceSelection = () => {
    userPicked.current = false;
    setWorkspaceId(null);
    qc.invalidateQueries();
  };

  const active =
    (workspaceId ? list.find((w) => w.id === workspaceId) : undefined) ??
    (wsList?.length ? latestWorkspace(wsList) : undefined) ??
    (USE_MOCK ? defaultWorkspaces[0] : undefined) ??
    EMPTY_WORKSPACE;

  return (
    <AppCtx.Provider
      value={{
        workspace: active,
        setWorkspace,
        clearWorkspaceSelection,
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
