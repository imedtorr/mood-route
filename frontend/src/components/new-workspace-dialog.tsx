import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateWorkspace } from "@/lib/api/hooks";
import { useApp } from "@/lib/app-context";
import { COUNTRY_OPTIONS, countryToFlag, defaultTripName } from "@/lib/countries";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
};

export function NewWorkspaceDialog({ open, onOpenChange, onCreated }: Props) {
  const { setWorkspace } = useApp();
  const createWorkspace = useCreateWorkspace();

  const [country, setCountry] = useState("");
  const [city, setCity] = useState("");
  const [name, setName] = useState("");

  const suggestedName = country ? defaultTripName(country) : "";

  useEffect(() => {
    if (!open) {
      setCountry("");
      setCity("");
      setName("");
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedCountry = country.trim();
    const trimmedCity = city.trim();
    if (!trimmedCountry || !trimmedCity) {
      toast.error("Please enter a country and city");
      return;
    }

    try {
      const ws = await createWorkspace.mutateAsync({
        country: trimmedCountry,
        city: trimmedCity,
        name: name.trim() || undefined,
        flag: countryToFlag(trimmedCountry),
      });
      setWorkspace(ws);
      toast.success(`Workspace "${ws.name}" created`);
      onOpenChange(false);
      onCreated?.();
    } catch {
      toast.error("Failed to create workspace");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-serif">New Workspace</DialogTitle>
          <DialogDescription>
            One workspace per city trip. Trip name is optional — leave blank to auto-generate.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="country">Country</Label>
            <Select value={country} onValueChange={setCountry}>
              <SelectTrigger id="country">
                <SelectValue placeholder="Select a country" />
              </SelectTrigger>
              <SelectContent>
                {COUNTRY_OPTIONS.map((c) => (
                  <SelectItem key={c.name} value={c.name}>
                    <span className="flex items-center gap-2">
                      <span>{c.flag}</span>
                      <span>{c.name}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="city">City</Label>
            <Input
              id="city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="Shanghai"
              autoComplete="off"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="trip-name">Trip name (optional)</Label>
            <Input
              id="trip-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={suggestedName || "China 2026"}
              autoComplete="off"
            />
            {suggestedName && !name && (
              <p className="text-xs text-muted-foreground">
                Default: {suggestedName}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createWorkspace.isPending}>
              {createWorkspace.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
