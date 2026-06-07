import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { Link2, UploadCloud, Plus, Info } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { UploadCard } from "@/components/upload-card";
import { useAddFileUpload, useAddUrlUpload, useUploads } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Inbox — MoodRoute" }] }),
  component: InboxPage,
});

function InboxPage() {
  const { data: uploads = [], isLoading } = useUploads();
  const addUrl = useAddUrlUpload();
  const addFile = useAddFileUpload();
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function addInspiration() {
    if (!url.trim()) return;
    try {
      await addUrl.mutateAsync({ url: url.trim(), note: note.trim() });
      toast.success("Inspiration added — processing in background");
      setUrl("");
      setNote("");
    } catch {
      toast.error("Failed to add URL");
    }
  }

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return;
    try {
      await addFile.mutateAsync({ file: files[0], note: note.trim() });
      toast.success("Screenshot uploaded — agents are processing");
      setNote("");
    } catch {
      toast.error("Failed to upload screenshot");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Inbox"
        title="Inspiration Inbox"
        description="Drop links and screenshots from Pinterest, Instagram, or articles. MoodRoute parses them into structured places in the background."
      />

      <div className="mx-auto max-w-5xl px-4 py-6 md:px-8">
        <div className="grid gap-4 lg:grid-cols-5">
          <div className="rounded-2xl border border-border bg-card p-5 lg:col-span-3">
            <label className="text-sm font-medium text-foreground">Add inspiration</label>
            <div className="mt-2 flex gap-2">
              <div className="relative flex-1">
                <Link2 className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addInspiration()}
                  placeholder="Paste a Pinterest, Instagram, or article link…"
                  className="h-11 pl-9"
                />
              </div>
              <Button onClick={addInspiration} className="h-11 gap-1.5" disabled={addUrl.isPending}>
                <Plus className="size-4" />
                Add
              </Button>
            </div>

            <label className="mt-4 block text-sm font-medium text-foreground">
              Why I saved this <span className="font-normal text-muted-foreground">(optional)</span>
            </label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="A quick note helps the AI understand your taste…"
              className="mt-2 min-h-20 resize-none"
            />
          </div>

          <div className="lg:col-span-2">
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && fileRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                handleFiles(e.dataTransfer.files);
              }}
              className={cn(
                "flex h-full min-h-44 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition-colors",
                dragging ? "border-primary bg-primary/5" : "border-border bg-card",
              )}
            >
              <span className="flex size-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
                <UploadCloud className="size-6" />
              </span>
              <p className="mt-3 text-sm font-medium text-foreground">Drop screenshots here</p>
              <p className="mt-1 text-xs text-muted-foreground">
                or click to browse — PNG, JPG up to 10MB
              </p>
            </div>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Info className="size-3.5" />
          Uploads are automatically processed in the background.
        </div>

        <div className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-serif text-xl font-semibold">Recent uploads</h2>
            <span className="text-sm text-muted-foreground">
              {isLoading ? "…" : `${uploads.length} items`}
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {uploads.map((u) => (
              <UploadCard key={u.id} upload={u} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
