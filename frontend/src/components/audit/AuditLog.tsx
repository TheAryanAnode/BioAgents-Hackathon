import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Download, X } from "lucide-react";
import { useStore } from "../../stores/useStore";
import { cn, formatTime } from "../../lib/utils";
import type { AuditEntry } from "../../lib/types";

export function AuditLog() {
  const open = useStore((s) => s.auditOpen);
  const toggle = useStore((s) => s.toggleAudit);
  const audit = useStore((s) => s.audit);
  const query = useStore((s) => s.query);
  const [agentFilter, setAgentFilter] = useState<string>("all");

  const agents = useMemo(
    () => ["all", ...Array.from(new Set(audit.map((a) => a.agent)))],
    [audit],
  );
  const filtered = audit.filter(
    (a) => agentFilter === "all" || a.agent === agentFilter,
  );

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ query, audit }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `synthesisos-audit-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ height: 0 }}
          animate={{ height: "40vh" }}
          exit={{ height: 0 }}
          transition={{ duration: 0.2, ease: [0.25, 0, 0, 1] }}
          className="z-30 overflow-hidden border-t border-border bg-card"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-border px-6 py-3">
              <div className="flex items-center gap-3">
                <span className="h-1 w-10 bg-accent" />
                <span className="label-mono">Audit log — {audit.length} actions</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="hidden items-center gap-1 sm:flex">
                  {agents.map((a) => (
                    <button
                      key={a}
                      onClick={() => setAgentFilter(a)}
                      className={cn(
                        "border px-2 py-1 font-mono text-[9px] uppercase tracking-widest transition-colors",
                        agentFilter === a
                          ? "border-accent text-accent"
                          : "border-border text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {a}
                    </button>
                  ))}
                </div>
                <button
                  onClick={exportJson}
                  className="flex items-center gap-1.5 border border-border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-accent hover:text-accent"
                >
                  <Download size={12} strokeWidth={1.5} /> Export
                </button>
                <button
                  onClick={toggle}
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Close audit log"
                >
                  <X size={18} strokeWidth={1.5} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-2 font-mono text-xs">
              {filtered.length === 0 && (
                <p className="px-2 py-8 text-center uppercase tracking-widest text-muted-foreground">
                  no actions yet
                </p>
              )}
              {filtered
                .slice()
                .reverse()
                .map((e) => (
                  <AuditRow key={e.id} entry={e} />
                ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const [open, setOpen] = useState(false);
  const hasDetail = entry.params && Object.keys(entry.params).length > 0;
  return (
    <div className="border-b border-border/50">
      <button
        onClick={() => hasDetail && setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-2 py-2 text-left transition-colors hover:bg-muted"
      >
        <span className="shrink-0 text-muted-foreground">{formatTime(entry.ts)}</span>
        <span
          className={cn(
            "shrink-0 uppercase tracking-widest",
            entry.status === "error"
              ? "text-contradict"
              : entry.status === "running"
                ? "text-accent"
                : "text-support",
          )}
        >
          {entry.agent}
        </span>
        <span className="truncate text-foreground">{entry.action}</span>
        <span className="ml-auto shrink-0 truncate text-muted-foreground">{entry.detail}</span>
        {typeof entry.durationMs === "number" && (
          <span className="shrink-0 text-muted-foreground">{entry.durationMs}ms</span>
        )}
        {hasDetail && (
          <ChevronDown
            size={14}
            strokeWidth={1.5}
            className={cn("shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
          />
        )}
      </button>
      {open && hasDetail && (
        <pre className="overflow-x-auto bg-background px-4 py-3 text-[11px] leading-relaxed text-muted-foreground">
          {JSON.stringify(entry.params, null, 2)}
        </pre>
      )}
    </div>
  );
}
