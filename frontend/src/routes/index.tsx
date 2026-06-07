import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { Link2, UploadCloud, Plus, Info, MapPin } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { UploadCard } from "@/components/upload-card";
import { useAddFileUpload, useAddTextUpload, useAddUrlUpload, useUploads } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const BLOCKED_URL_HOSTS = ["instagram.com", "pinterest.com", "pin.it"];

function isBlockedSocialUrl(url: string): boolean {
  const lower = url.toLowerCase();
  return BLOCKED_URL_HOSTS.some((host) => lower.includes(host));
}

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Inbox — MoodRoute" }] }),
  component: InboxPage,
});

function InboxPage() {
  const { data: uploads = [], isLoading } = useUploads();
  const addUrl = useAddUrlUpload();
  const addFile = useAddFileUpload();
  const addText = useAddTextUpload();
  const [url, setUrl] = useState("");
  const [placeQuery, setPlaceQuery] = useState("");
  const [note, setNote] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function addArticle() {
    if (!url.trim()) return;
    if (isBlockedSocialUrl(url)) {
      toast.error("Only article links are supported. For social media posts, upload a screenshot instead.");
      return;
    }
    try {
      await addUrl.mutateAsync({ url: url.trim(), note: note.trim() });
      toast.success("Article added — processing in the background");
      setUrl("");
      setNote("");
    } catch {
      toast.error("Could not add link");
    }
  }

  async function addPlace() {
    if (!placeQuery.trim()) return;
    try {
      await addText.mutateAsync({ query: placeQuery.trim(), note: note.trim() });
      toast.success("Place added — agents are gathering details");
      setPlaceQuery("");
      setNote("");
    } catch {
      toast.error("Could not add place");
    }
  }

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return;
    try {
      await addFile.mutateAsync({ file: files[0], note: note.trim() });
      toast.success("Screenshot uploaded — agents are processing");
      setNote("");
    } catch {
      toast.error("Could not upload screenshot");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Inbox"
        title="Inspiration Inbox"
        description="Upload a screenshot, paste an article link, or enter a place name — MoodRoute will save it in the Places tab."
      />

      <div className="mx-auto max-w-5xl px-4 py-6 md:px-8">
        <Tabs defaultValue="photo" className="grid gap-4 lg:grid-cols-5">
          <div className="rounded-2xl border border-border bg-card p-5 lg:col-span-3">
            <TabsList className="mb-4 grid w-full grid-cols-3">
              <TabsTrigger value="photo">Photo</TabsTrigger>
              <TabsTrigger value="article">Article</TabsTrigger>
              <TabsTrigger value="place">Place</TabsTrigger>
            </TabsList>

            <TabsContent value="article" className="mt-0">
              <label className="text-sm font-medium text-foreground">Article link</label>
              <div className="mt-2 flex gap-2">
                <div className="relative flex-1">
                  <Link2 className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addArticle()}
                    placeholder="https://en.wikipedia.org/wiki/Yanaka,_Tokyo"
                    className="h-11 pl-9"
                  />
                </div>
                <Button onClick={addArticle} className="h-11 gap-1.5" disabled={addUrl.isPending}>
                  <Plus className="size-4" />
                  Add
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="place" className="mt-0">
              <label className="text-sm font-medium text-foreground">Place name</label>
              <div className="mt-2 flex gap-2">
                <div className="relative flex-1">
                  <MapPin className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={placeQuery}
                    onChange={(e) => setPlaceQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addPlace()}
                    placeholder="Fuglen Tokyo, Blue Bottle Aoyama…"
                    className="h-11 pl-9"
                  />
                </div>
                <Button onClick={addPlace} className="h-11 gap-1.5" disabled={addText.isPending}>
                  <Plus className="size-4" />
                  Add
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="photo" className="mt-0">
              <p className="text-sm text-muted-foreground">
                Drag a screenshot to the area on the right, or click it.
              </p>
            </TabsContent>

            <label className="mt-4 block text-sm font-medium text-foreground">
              Note <span className="font-normal text-muted-foreground">(optional)</span>
            </label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="A short note helps the AI understand your taste…"
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
              <p className="mt-3 text-sm font-medium text-foreground">Drag a screenshot here</p>
              <p className="mt-1 text-xs text-muted-foreground">
                or click — PNG, JPG up to 10MB
              </p>
            </div>
          </div>
        </Tabs>

        <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Info className="size-3.5" />
          Uploads are processed automatically in the background.
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
