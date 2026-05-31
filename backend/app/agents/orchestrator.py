from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.analysis import AnalysisAgent
from app.agents.base import AgentContext
from app.agents.commercial import CommercialAgent
from app.agents.evidence import EvidenceAgent
from app.agents.graph_builder import GraphBuilderAgent
from app.agents.hypothesis import HypothesisAgent
from app.agents.ingestion import IngestionAgent
from app.core.llm import get_llm
from app.services.embeddings import EmbeddingClient, VectorStore
from app.services.session_store import Session

# Shared singletons (vector store keeps per-corpus collections in memory).
_embedder = EmbeddingClient()
_vectors = VectorStore(_embedder)
_contexts: dict[str, AgentContext] = {}


def get_vectors() -> VectorStore:
    return _vectors


def get_context(session_id: str) -> AgentContext | None:
    return _contexts.get(session_id)


def make_context(session: Session) -> AgentContext:
    ctx = AgentContext(session=session, llm=get_llm(), vectors=_vectors)
    _contexts[session.state.sessionId] = ctx
    return ctx


class PState(TypedDict, total=False):
    step: str


def _build_pipeline(ctx: AgentContext):
    ingestion = IngestionAgent()
    analysis = AnalysisAgent()
    graph_builder = GraphBuilderAgent()
    hypothesis = HypothesisAgent()
    evidence = EvidenceAgent()
    commercial = CommercialAgent()

    async def n_ingestion(state: PState) -> PState:
        await ingestion.run_query(ctx)
        return {"step": "ingestion"}

    async def n_analysis(state: PState) -> PState:
        await analysis.run(ctx)
        return {"step": "analysis"}

    async def n_graph(state: PState) -> PState:
        await graph_builder.run(ctx)
        return {"step": "graph"}

    async def n_hypothesis(state: PState) -> PState:
        await hypothesis.run(ctx, n=3)
        ctx.work["hypothesis_agent"] = hypothesis
        return {"step": "hypothesis"}

    async def n_evidence(state: PState) -> PState:
        await evidence.run(ctx)
        return {"step": "evidence"}

    async def n_commercial(state: PState) -> PState:
        await commercial.run(ctx)
        return {"step": "commercial"}

    sg = StateGraph(PState)
    sg.add_node("ingestion", n_ingestion)
    sg.add_node("analysis", n_analysis)
    sg.add_node("graph", n_graph)
    sg.add_node("hypothesis", n_hypothesis)
    sg.add_node("evidence", n_evidence)
    sg.add_node("commercial", n_commercial)

    sg.add_edge(START, "ingestion")
    sg.add_edge("ingestion", "analysis")
    sg.add_edge("analysis", "graph")
    sg.add_edge("graph", "hypothesis")
    sg.add_edge("hypothesis", "evidence")
    sg.add_edge("evidence", "commercial")
    sg.add_edge("commercial", END)
    return sg.compile()


async def run_pipeline(session: Session) -> None:
    ctx = make_context(session)
    try:
        pipeline = _build_pipeline(ctx)
        await pipeline.ainvoke({"step": "start"})
        await ctx.stage("done")
        await session.emit({"type": "done", "payload": {}})
    except Exception as exc:  # never leave the client hanging
        await ctx.audit("orchestrator", "Pipeline error", detail=str(exc)[:200], status="error")
        await session.emit({"type": "error", "payload": {"message": str(exc)[:200]}})
    finally:
        session.done = True
