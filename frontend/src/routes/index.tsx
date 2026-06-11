import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { Link2, UploadCloud, Plus, Info, MapPin, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { UploadCard } from "@/components/upload-card";
import { useAddFileUpload, useAddTextUpload, useAddUrlUpload, useUploads } from "@/lib/api/hooks";
import { useApp } from "@/lib/app-context";
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
  const { aesthetic } = useApp();
  const { data: uploads = [], isLoading } = useUploads();
  const addUrl = useAddUrlUpload();
  const addFile = useAddFileUpload();
  const addText = useAddTextUpload();
  const [url, setUrl] = useState("");
  const [placeQuery, setPlaceQuery] = useState("");
  const [note, setNote] = useState("");
  const [activeTab, setActiveTab] = useState("photo");
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
        <div
          className={cn(
            "rounded-2xl border p-5 shadow-[var(--shadow-card)]",
            aesthetic
              ? "border-primary/30 bg-gradient-to-br from-card to-accent/30"
              : "border-border bg-card",
          )}
        >
          <Tabs value={activeTab} onValueChange={setActiveTab}>
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
              <p className="mt-3 text-xs text-muted-foreground">
                Social media post?{" "}
                <button
                  type="button"
                  onClick={() => setActiveTab("photo")}
                  className="font-medium text-foreground underline-offset-2 hover:underline"
                >
                  Upload a screenshot instead
                </button>
              </p>
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
              <p className="mt-3 text-xs text-muted-foreground">
                Saved as an image?{" "}
                <button
                  type="button"
                  onClick={() => setActiveTab("photo")}
                  className="font-medium text-foreground underline-offset-2 hover:underline"
                >
                  Upload a screenshot instead
                </button>
              </p>
            </TabsContent>

            <TabsContent value="photo" className="mt-0">
              <div className="grid gap-5 lg:grid-cols-5">
                <div className="flex flex-col lg:col-span-3">
                  <h3 className="font-serif text-lg font-medium text-foreground">
                    Drop your inspiration
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Drag a screenshot to the area on the right, or click it.
                  </p>
                  <label className="mt-4 block text-sm font-medium text-foreground">
                    Note <span className="font-normal text-muted-foreground">(optional)</span>
                  </label>
                  <Textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="A short note helps the AI understand your taste…"
                    className="mt-2 min-h-20 flex-1 resize-none"
                  />
                  {aesthetic && (
                    <p className="mt-3 font-serif text-sm italic text-muted-foreground">
                      &ldquo;A café corner, a neon alley, a quiet courtyard.&rdquo;
                    </p>
                  )}
                </div>

                <div className="flex flex-col lg:col-span-2 lg:border-l lg:border-border/50 lg:pl-5">
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden"
                    onChange={(e) => handleFiles(e.target.files)}
                  />
                  <div
                    role="button"
                    tabIndex={addFile.isPending ? -1 : 0}
                    aria-busy={addFile.isPending}
                    onClick={() => !addFile.isPending && fileRef.current?.click()}
                    onKeyDown={(e) =>
                      !addFile.isPending && e.key === "Enter" && fileRef.current?.click()
                    }
                    onDragOver={(e) => {
                      if (addFile.isPending) return;
                      e.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(e) => {
                      if (addFile.isPending) return;
                      e.preventDefault();
                      setDragging(false);
                      handleFiles(e.dataTransfer.files);
                    }}
                    className={cn(
                      "flex min-h-52 flex-1 flex-col items-center justify-center rounded-2xl border border-border/60 p-6 text-center transition-all duration-200",
                      addFile.isPending
                        ? "cursor-wait border-primary/40 bg-primary/5"
                        : "cursor-pointer bg-gradient-to-br from-accent/25 to-muted/40 hover:border-primary/30 hover:from-accent/35",
                      !addFile.isPending &&
                        dragging &&
                        "scale-[1.01] border-primary/50 bg-primary/5 ring-2 ring-primary/20",
                      aesthetic && !addFile.isPending && !dragging && "to-accent/50",
                    )}
                  >
                    <span className="flex size-14 items-center justify-center rounded-full bg-accent text-accent-foreground ring-4 ring-background/80">
                      {addFile.isPending ? (
                        <Loader2 className="size-6 animate-spin" />
                      ) : (
                        <UploadCloud className="size-6" />
                      )}
                    </span>
                    <p className="mt-3 text-sm font-medium text-foreground">
                      {addFile.isPending ? "Uploading screenshot…" : "Drag a screenshot here"}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {addFile.isPending ? "Please wait" : "or click to browse"}
                    </p>
                  </div>
                  <div className="mt-3 flex justify-center">
                    <span className="inline-flex items-center rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground">
                      PNG, JPG · up to 10MB
                    </span>
                  </div>
                </div>
              </div>
            </TabsContent>

            {activeTab !== "photo" && (
              <>
                <label className="mt-4 block text-sm font-medium text-foreground">
                  Note <span className="font-normal text-muted-foreground">(optional)</span>
                </label>
                <Textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="A short note helps the AI understand your taste…"
                  className="mt-2 min-h-20 resize-none"
                />
              </>
            )}
          </Tabs>
        </div>

        <div className="mt-3 flex items-center gap-1.5 rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          <Info className="size-3.5 shrink-0" />
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
