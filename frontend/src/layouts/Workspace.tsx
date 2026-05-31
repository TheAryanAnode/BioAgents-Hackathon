import { useStore } from "../stores/useStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { Navbar, MobileNav } from "./Navbar";
import { StageBar } from "../components/StageBar";
import { GraphView } from "../components/graph/GraphView";
import { HypothesisPanel } from "../components/hypothesis/HypothesisPanel";
import { OpportunityDashboard } from "../components/dashboard/OpportunityDashboard";
import { ChatPanel } from "../components/chat/ChatPanel";
import { AuditLog } from "../components/audit/AuditLog";

export function Workspace({ onHome }: { onHome: () => void }) {
  const sessionId = useStore((s) => s.sessionId);
  const view = useStore((s) => s.view);
  useWebSocket(sessionId);

  return (
    <div className="flex h-screen flex-col">
      <Navbar onHome={onHome} />
      <StageBar />
      <main className="relative flex-1 overflow-hidden">
        {view === "graph" && <GraphView />}
        {view === "hypotheses" && <HypothesisPanel />}
        {view === "opportunities" && <OpportunityDashboard />}
        {view === "chat" && <ChatPanel />}
      </main>
      <AuditLog />
      <MobileNav />
    </div>
  );
}
