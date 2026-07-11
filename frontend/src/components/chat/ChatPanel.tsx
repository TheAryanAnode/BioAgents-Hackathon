import { useEffect, useRef, useState } from "react";
import { ExternalLink, Loader2, Send } from "lucide-react";
import { useStore } from "../../stores/useStore";
import { api } from "../../lib/api";
import { Badge } from "../ui/Card";
import { SOURCE_LABEL } from "../../lib/utils";
import type { ChatMessage } from "../../lib/types";

const SUGGESTIONS = [
  "What pathways connect these clusters?",
  "Which findings are most contested?",
  "What clinical trials target this subgroup?",
  "Explain this topic to a non-scientist",
];

export function ChatPanel() {
  const sessionId = useStore((s) => s.sessionId);
  const chat = useStore((s) => s.chat);
  const addChat = useStore((s) => s.addChat);
  const selectedNode = useStore((s) => s.selectedNode);
  const nodes = useStore((s) => s.graph.nodes);
  const geminiLive = useStore((s) => s.geminiLive);
  const geminiQuotaExhausted = useStore((s) => s.geminiQuotaExhausted);
  const selectNode = useStore((s) => s.selectNode);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, busy]);

  const send = async (text: string) => {
    const msg = text.trim();
    if (!msg || !sessionId || busy) return;
    addChat({ id: crypto.randomUUID(), role: "user", content: msg, ts: new Date().toISOString() });
    setValue("");
    setBusy(true);
    try {
      const res = await api.chat(sessionId, msg, selectedNode?.id);
      addChat({
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.content,
        ts: new Date().toISOString(),
        citations: res.citations,
      });
    } catch (e: any) {
      addChat({
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Error: ${e.message ?? "request failed"}`,
        ts: new Date().toISOString(),
      });
    } finally {
      setBusy(false);
    }
  };

  const jumpTo = (paperId: string) => {
    const node = nodes.find((n) => n.id === paperId);
    if (node) {
      selectNode(node);
      useStore.getState().setView("graph");
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="h-1 w-10 bg-accent" />
          <span className="label-mono">Research Q&amp;A</span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {geminiQuotaExhausted
            ? "Rate limited — wait ~1 min"
            : geminiLive
              ? "Gemini + corpus"
              : "Corpus only"}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {chat.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <p className="max-w-md text-lg leading-normal text-muted-foreground">
              Ask about your synthesized literature. Each message uses one Gemini request when configured.
            </p>
            <div className="mt-8 flex flex-col items-center gap-3">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-accent hover:text-foreground">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {chat.map((m) => (
            <div key={m.id} className={m.role === "user" ? "pl-8 md:pl-16" : ""}>
              <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {m.role === "user" ? "You" : "SynthesisOS"}
              </div>
              <div className={m.role === "user" ? "border-l-2 border-accent pl-4 text-base leading-normal" : "text-base leading-normal text-foreground/90 whitespace-pre-wrap"}>
                {m.content}
              </div>
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  {m.citations.map((c) => (
                    <div key={c.paperId} className="flex flex-wrap items-center gap-2">
                      <button onClick={() => jumpTo(c.paperId)}>
                        <Badge tone={c.source === "user_pdf" ? "support" : "accent"}>
                          {SOURCE_LABEL[c.source] ?? c.source}
                        </Badge>
                      </button>
                      {c.url ? (
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm text-accent underline underline-offset-2 hover:opacity-80"
                        >
                          {c.title.length > 48 ? c.title.slice(0, 46) + "…" : c.title}
                          <ExternalLink size={12} strokeWidth={1.5} />
                        </a>
                      ) : (
                        <button onClick={() => jumpTo(c.paperId)} className="text-sm text-muted-foreground hover:text-foreground">
                          {c.title.length > 48 ? c.title.slice(0, 46) + "…" : c.title}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 size={16} strokeWidth={1.5} className="animate-spin" />
              <span className="font-mono text-xs uppercase tracking-widest">thinking…</span>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(value); }} className="flex items-center gap-3 border-t border-border px-6 py-4">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a research question…"
          className="h-12 flex-1 border border-border bg-input px-4 text-base text-foreground outline-none focus:border-accent"
        />
        <button type="submit" disabled={busy || !value.trim()} className="flex h-12 w-12 items-center justify-center bg-accent text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-40" aria-label="Send">
          <Send size={18} strokeWidth={1.5} />
        </button>
      </form>
    </div>
  );
}
