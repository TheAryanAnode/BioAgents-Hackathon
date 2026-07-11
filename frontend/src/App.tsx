import { useEffect } from "react";
import { Workspace } from "./layouts/Workspace";
import { useStore } from "./stores/useStore";
import { api } from "./lib/api";

export default function App() {
  const setSession = useStore((s) => s.setSession);
  const setQuery = useStore((s) => s.setQuery);
  const setRunning = useStore((s) => s.setRunning);
  const setLlm = useStore((s) => s.setLlm);
  const setView = useStore((s) => s.setView);
  const reset = useStore((s) => s.reset);
  const llmLive = useStore((s) => s.llmLive);

  useEffect(() => {
    api
      .health()
      .then((h) => setLlm(h.llm, h.llmQuotaExhausted, h.llmModel))
      .catch(() => setLlm(false));
  }, [setLlm]);

  // Pointer-reactive aurora: drive the radial-gradient origin from the cursor.
  // rAF-throttled and writes two CSS vars only — negligible cost.
  useEffect(() => {
    let raf = 0;
    let x = 0;
    let y = 0;
    const onMove = (e: PointerEvent) => {
      x = e.clientX - window.innerWidth / 2;
      y = e.clientY - window.innerHeight / 2;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        document.body.style.setProperty("--posX", String(x));
        document.body.style.setProperty("--posY", String(y));
      });
    };
    window.addEventListener("pointermove", onMove);
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  const start = async (query: string) => {
    reset();
    setQuery(query);
    setRunning(true);
    setView("graph");
    useStore.setState({ stage: "ingestion" });
    try {
      const { sessionId } = await api.startResearch(query);
      setSession(sessionId);
    } catch (e) {
      setRunning(false);
      console.error(e);
    }
  };

  return (
    <div className="grain min-h-screen">
      <div className="aurora" aria-hidden />
      <div className="aurora-scrim" aria-hidden />
      <Workspace onStart={start} llmLive={llmLive} />
    </div>
  );
}
