import { motion } from "framer-motion";
import { Home, ScrollText, Sparkles } from "lucide-react";
import { useStore, type View } from "../stores/useStore";
import { cn } from "../lib/utils";

// Home + Auto are always-available modes; the session views may be empty until
// a research run exists (that's fine — they hydrate live).
const MODE_VIEWS: { id: View; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "auto", label: "Auto" },
];
const SESSION_VIEWS: { id: View; label: string }[] = [
  { id: "graph", label: "Graph" },
  { id: "hypotheses", label: "Hypotheses" },
  { id: "chat", label: "Chat" },
];
const ALL_VIEWS = [...MODE_VIEWS, ...SESSION_VIEWS];

export function Navbar() {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const query = useStore((s) => s.query);
  const auditOpen = useStore((s) => s.auditOpen);
  const toggleAudit = useStore((s) => s.toggleAudit);
  const auditCount = useStore((s) => s.audit.length);

  return (
    <header className="z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur md:px-8">
      <button
        onClick={() => setView("home")}
        className="flex items-center gap-3 transition-opacity hover:opacity-80"
      >
        <span className="h-5 w-1.5 bg-accent" />
        <span className="font-sans text-lg font-extrabold tracking-tight">
          SYNTHESIS<span className="text-accent">OS</span>
        </span>
      </button>

      <nav className="hidden items-center gap-1 md:flex">
        {MODE_VIEWS.map((v) => (
          <NavTab key={v.id} v={v} active={view === v.id} onClick={() => setView(v.id)} />
        ))}
        <span className="mx-1 h-4 w-px bg-border" />
        {SESSION_VIEWS.map((v) => (
          <NavTab key={v.id} v={v} active={view === v.id} onClick={() => setView(v.id)} />
        ))}
      </nav>

      <div className="flex items-center gap-4">
        {query && (
          <span className="hidden max-w-[200px] truncate font-mono text-xs uppercase tracking-widest text-muted-foreground lg:inline">
            ▸ {query}
          </span>
        )}
        <button
          onClick={toggleAudit}
          className={cn(
            "flex items-center gap-2 border px-3 py-2 font-mono text-xs uppercase tracking-widest transition-colors duration-150",
            auditOpen
              ? "border-accent text-accent"
              : "border-border text-muted-foreground hover:border-border-hover hover:text-foreground",
          )}
        >
          <ScrollText size={16} strokeWidth={1.5} />
          <span className="hidden sm:inline">Audit</span>
          {auditCount > 0 && <span className="text-foreground">{auditCount}</span>}
        </button>
      </div>
    </header>
  );
}

function NavTab({
  v,
  active,
  onClick,
}: {
  v: { id: View; label: string };
  active: boolean;
  onClick: () => void;
}) {
  const Icon = v.id === "home" ? Home : v.id === "auto" ? Sparkles : null;
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative flex items-center gap-1.5 px-4 py-2 font-mono text-xs uppercase tracking-widest transition-colors duration-150",
        active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {Icon && <Icon size={13} strokeWidth={1.5} />}
      {v.label}
      {active && (
        <motion.span
          layoutId="nav-underline"
          className="absolute bottom-0 left-2 right-2 h-0.5 bg-accent"
          transition={{ duration: 0.2, ease: [0.25, 0, 0, 1] }}
        />
      )}
    </button>
  );
}

export function MobileNav() {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  return (
    <nav className="flex items-center justify-around border-t border-border bg-background/90 backdrop-blur md:hidden">
      {ALL_VIEWS.map((v) => (
        <button
          key={v.id}
          onClick={() => setView(v.id)}
          className={cn(
            "flex-1 py-3 font-mono text-[10px] uppercase tracking-widest transition-colors",
            view === v.id ? "text-accent" : "text-muted-foreground",
          )}
        >
          {v.label}
        </button>
      ))}
    </nav>
  );
}
