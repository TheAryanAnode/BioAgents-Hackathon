import { useEffect } from "react";
import { Landing } from "./pages/Landing";
import { Workspace } from "./layouts/Workspace";
import { useStore } from "./stores/useStore";
import { api } from "./lib/api";

export default function App() {
  const sessionId = useStore((s) => s.sessionId);
  const setSession = useStore((s) => s.setSession);
  const setQuery = useStore((s) => s.setQuery);
  const setRunning = useStore((s) => s.setRunning);
  const setGemini = useStore((s) => s.setGemini);
  const reset = useStore((s) => s.reset);
  const geminiLive = useStore((s) => s.geminiLive);

  useEffect(() => {
    api
      .health()
      .then((h) => setGemini(h.gemini, h.geminiQuotaExhausted))
      .catch(() => setGemini(false));
  }, [setGemini]);

  const start = async (query: string) => {
    reset();
    setQuery(query);
    setRunning(true);
    useStore.setState({ stage: "ingestion" });
    try {
      const { sessionId } = await api.startResearch(query);
      setSession(sessionId);
    } catch (e) {
      setRunning(false);
      console.error(e);
    }
  };

  const goHome = () => {
    setSession("");
    useStore.setState({ sessionId: null });
    reset();
    setQuery("");
  };

  return (
    <div className="grain min-h-screen">
      {sessionId ? (
        <Workspace onHome={goHome} />
      ) : (
        <Landing onStart={start} geminiLive={geminiLive} />
      )}
    </div>
  );
}
