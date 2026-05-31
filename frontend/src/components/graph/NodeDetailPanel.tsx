import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, X } from "lucide-react";
import { useStore } from "../../stores/useStore";
import { Badge } from "../ui/Card";
import { SOURCE_LABEL } from "../../lib/utils";

export function NodeDetailPanel() {
  const node = useStore((s) => s.selectedNode);
  const selectNode = useStore((s) => s.selectNode);

  return (
    <AnimatePresence>
      {node && (
        <motion.aside
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ duration: 0.2, ease: [0.25, 0, 0, 1] }}
          className="absolute right-0 top-0 z-20 flex h-full w-full max-w-md flex-col border-l border-border bg-card"
        >
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <div className="flex items-center gap-2">
              <Badge tone={node.type === "concept" ? "accent" : "muted"}>
                {node.type}
              </Badge>
              {node.source && (
                <Badge tone={node.source === "user_pdf" ? "support" : "muted"}>
                  {SOURCE_LABEL[node.source] ?? node.source}
                </Badge>
              )}
            </div>
            <button
              onClick={() => selectNode(null)}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Close"
            >
              <X size={20} strokeWidth={1.5} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-6">
            <h2 className="text-balance text-2xl font-bold leading-tight tracking-tight">
              {node.label}
            </h2>

            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 font-mono text-xs uppercase tracking-widest text-muted-foreground">
              {node.year && <span>Year {node.year}</span>}
              {typeof node.citationCount === "number" && (
                <span>{node.citationCount} citations</span>
              )}
              {typeof node.centrality === "number" && (
                <span>centrality {(node.centrality * 100).toFixed(0)}</span>
              )}
              {typeof node.paperCount === "number" && (
                <span>{node.paperCount} papers</span>
              )}
            </div>

            {node.authors && node.authors.length > 0 && (
              <p className="mt-6 text-sm text-muted-foreground">
                {node.authors.join(", ")}
              </p>
            )}

            {node.summary && (
              <>
                <div className="mt-8 flex items-center gap-3">
                  <span className="h-1 w-10 bg-accent" />
                  <span className="label-mono">
                    {node.type === "concept" ? "Definition" : "Summary"}
                  </span>
                </div>
                <p className="mt-3 text-base leading-normal text-foreground/90">
                  {node.summary}
                </p>
              </>
            )}

            {node.url && (
              <a
                href={node.url}
                target="_blank"
                rel="noreferrer"
                className="mt-8 inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-accent transition-opacity hover:opacity-80"
              >
                <ExternalLink size={14} strokeWidth={1.5} /> View source
              </a>
            )}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
