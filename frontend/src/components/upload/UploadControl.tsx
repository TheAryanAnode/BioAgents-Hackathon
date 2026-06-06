import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FileUp, Loader2, Upload, X } from "lucide-react";
import { api } from "../../lib/api";
import { useStore } from "../../stores/useStore";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";

export function UploadControl() {
  const sessionId = useStore((s) => s.sessionId);
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [doi, setDoi] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setFile(null);
    setTitle("");
    setDoi("");
    setError(null);
  };

  const submit = async () => {
    if (!file || !sessionId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.uploadPaper(sessionId, file, { title, doi });
      const state = await api.getSession(sessionId);
      useStore.getState().loadSession(state);
      setOpen(false);
      reset();
    } catch (e: any) {
      setError(e.message ?? "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-2"
      >
        <Upload size={14} strokeWidth={1.5} /> Upload
      </Button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-6 backdrop-blur"
            onClick={() => !busy && setOpen(false)}
          >
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              transition={{ duration: 0.2, ease: [0.25, 0, 0, 1] }}
              className="w-full max-w-lg border border-border bg-card p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="mb-2 flex items-center gap-3">
                    <span className="h-1 w-10 bg-accent" />
                    <span className="label-mono">Extend the corpus</span>
                  </div>
                  <h2 className="text-3xl font-bold tracking-tight">
                    Upload a paper
                  </h2>
                </div>
                <button
                  onClick={() => !busy && setOpen(false)}
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Close"
                >
                  <X size={20} strokeWidth={1.5} />
                </button>
              </div>

              <p className="mt-3 text-sm leading-normal text-muted-foreground">
                Your PDF is parsed, embedded, and added to the same knowledge
                graph and evidence layer as the API-sourced literature.
              </p>

              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  const f = e.dataTransfer.files?.[0];
                  if (f) setFile(f);
                }}
                onClick={() => inputRef.current?.click()}
                className={`mt-6 flex cursor-pointer flex-col items-center justify-center border border-dashed py-10 transition-colors ${
                  dragging ? "border-accent bg-accent/5" : "border-border hover:border-border-hover"
                }`}
              >
                <FileUp size={28} strokeWidth={1.5} className="text-muted-foreground" />
                <p className="mt-3 text-sm">
                  {file ? (
                    <span className="text-foreground">{file.name}</span>
                  ) : (
                    <span className="text-muted-foreground">
                      Drop a PDF here, or click to browse
                    </span>
                  )}
                </p>
                <input
                  ref={inputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="label-mono mb-2 block">Title (optional)</label>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Override title"
                  />
                </div>
                <div>
                  <label className="label-mono mb-2 block">DOI / arXiv (optional)</label>
                  <Input
                    value={doi}
                    onChange={(e) => setDoi(e.target.value)}
                    placeholder="10.xxxx/…"
                  />
                </div>
              </div>

              {error && (
                <p className="mt-4 font-mono text-xs uppercase tracking-widest text-contradict">
                  {error}
                </p>
              )}

              <div className="mt-8 flex items-center justify-end gap-6">
                <Button variant="ghost" size="sm" onClick={() => setOpen(false)} disabled={busy}>
                  Cancel
                </Button>
                <Button size="sm" onClick={submit} disabled={!file || busy}>
                  {busy ? (
                    <>
                      <Loader2 size={14} strokeWidth={1.5} className="animate-spin" />
                      Ingesting
                    </>
                  ) : (
                    <>Ingest paper</>
                  )}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
