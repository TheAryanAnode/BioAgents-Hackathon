import { useStore } from "../stores/useStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { Navbar, MobileNav } from "./Navbar";
import { StageBar } from "../components/StageBar";
import { GraphView } from "../components/graph/GraphView";
import { HypothesisPanel } from "../components/hypothesis/HypothesisPanel";
import { ChatPanel } from "../components/chat/ChatPanel";
import { AuditLog } from "../components/audit/AuditLog";
import { Landing } from "../pages/Landing";
import { AutoMode } from "../pages/AutoMode";

/**
 * Persistent app shell. The navbar (Home · Auto · Graph · Hypotheses · Chat) is
 * always visible; session views render empty until a research run hydrates them.
 */
export function Workspace({
  onStart,
  geminiLive,
}: {
  onStart: (q: string) => void;
  geminiLive: boolean;
}) {
  const sessionId = useStore((s) => s.sessionId);
  const view = useStore((s) => s.view);
  useWebSocket(sessionId);

  return (
    <div className="flex h-screen flex-col">
      <Navbar />
      <StageBar />
      <main className="relative flex-1 overflow-hidden">
        {view === "home" && <Landing onStart={onStart} geminiLive={geminiLive} />}
        {view === "auto" && <AutoMode onStart={onStart} geminiLive={geminiLive} />}
        {view === "graph" && <GraphView />}
        {view === "hypotheses" && <HypothesisPanel />}
        {view === "chat" && <ChatPanel />}
      </main>
      <AuditLog />
      <MobileNav />
    </div>
  );
}
