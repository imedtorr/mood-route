import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Search, Sparkles, PanelRight } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { usePlaceSearch } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";

export function Topbar() {
  const navigate = useNavigate();
  const { aesthetic, setAesthetic, agentOpen, setAgentOpen } = useApp();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const { data: searchResult } = usePlaceSearch(query);

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-sm md:px-6">
      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          placeholder="Search places and routes…"
          className="h-10 w-full rounded-full border border-border bg-card pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring/40"
        />
        {focused && query.length >= 2 && searchResult?.places && (
          <div className="absolute left-0 right-0 top-11 z-20 max-h-64 overflow-y-auto rounded-xl border border-border bg-popover p-2 shadow-lg">
            {searchResult.places.length === 0 && (
              <p className="px-2 py-3 text-xs text-muted-foreground">No places found</p>
            )}
            {searchResult.places.map((p) => (
              <button
                key={p.id}
                type="button"
                className="flex w-full flex-col rounded-lg px-2 py-2 text-left text-sm hover:bg-muted"
                onMouseDown={() => {
                  setQuery("");
                  navigate({ to: "/places" });
                }}
              >
                <span className="font-medium">{p.title}</span>
                <span className="text-xs text-muted-foreground">
                  {p.city} · {p.category}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-3">
        <label
          className={cn(
            "flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
            aesthetic
              ? "border-primary/30 bg-primary/10 text-primary"
              : "border-border bg-card text-muted-foreground",
          )}
        >
          <Sparkles className="size-4" />
          <span className="hidden sm:inline">Aesthetic Mode</span>
          <Switch
            checked={aesthetic}
            onCheckedChange={setAesthetic}
            aria-label="Toggle aesthetic mode"
          />
        </label>

        <Button
          variant="ghost"
          size="icon"
          className="rounded-full lg:hidden"
          onClick={() => setAgentOpen(!agentOpen)}
          aria-label="Toggle agent activity"
          aria-pressed={agentOpen}
        >
          <PanelRight className="size-5" />
        </Button>
      </div>
    </header>
  );
}
