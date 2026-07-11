from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents import chat as chat_agent
from app.agents.analysis import AnalysisAgent
from app.agents.commercial import CommercialAgent
from app.agents.evidence import EvidenceAgent
from app.agents.graph_builder import GraphBuilderAgent
from app.agents.hypothesis import HypothesisAgent
from app.agents.ingestion import IngestionAgent
from app.agents.enrich import enrich_hypothesis
from app.agents.investigation import investigate as investigate_hypothesis
from app.agents.orchestrator import get_context, make_context, run_pipeline
from app.agents.post_upload import after_paper_added
from app.agents.report import generate as generate_report
from app.core.config import get_settings
from app.core.llm import get_llm
from app.db.database import SessionLocal, UploadRow
from app.models.schemas import (
    ChatRequest,
    GraphNode,
    ResearchRequest,
    SessionState,
)
from app.services import pdf_ingest
from app.services.paper_urls import resolve_paper_url
from app.services.session_store import store

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    llm = get_llm()
    s = get_settings()
    return {
        "status": "ok",
        "llm": llm.enabled,
        "llmProvider": llm.provider,
        "llmModel": s.nebius_model,
        "llmPipeline": llm.pipeline_llm_allowed,
        "llmQuotaExhausted": llm.quota_exhausted,
        "llmMaxRpm": s.llm_max_rpm,
    }


@router.post("/research")
async def start_research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "query is required")
    session_id = uuid.uuid4().hex[:12]
    session = store.create(session_id, req.query.strip())
    # Serverless (Vercel): await pipeline — background tasks are killed after response.
    if os.getenv("VERCEL"):
        await run_pipeline(session)
    else:
        asyncio.create_task(run_pipeline(session))
    return {"sessionId": session_id}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> SessionState:
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    return session.state


@router.post("/sessions/{session_id}/hypotheses")
async def generate_hypothesis(session_id: str):
    ctx = get_context(session_id)
    if not ctx:
        raise HTTPException(404, "session not ready")
    agent: HypothesisAgent = ctx.work.get("hypothesis_agent") or HypothesisAgent()
    h = await agent.propose_one(ctx)
    await EvidenceAgent().evaluate(ctx, h)
    CommercialAgent().attach_opportunity(ctx, h)
    ctx.session.state.hypotheses.append(h)
    await ctx.session.emit({"type": "hypotheses", "payload": [x.model_dump() for x in ctx.session.state.hypotheses]})
    await ctx.audit("hypothesis", "Manual hypothesis added", detail=h.statement[:80])
    return h


@router.post("/sessions/{session_id}/hypotheses/{hypothesis_id}/enrich")
async def enrich_hypothesis_route(session_id: str, hypothesis_id: str):
    """Single Nebius LLM call when user selects a hypothesis — not used by the auto pipeline."""
    ctx = get_context(session_id)
    if not ctx:
        raise HTTPException(404, "session not ready")
    h = next((x for x in ctx.session.state.hypotheses if x.id == hypothesis_id), None)
    if not h:
        raise HTTPException(404, "hypothesis not found")
    h = await enrich_hypothesis(ctx, h)
    await ctx.session.emit({
        "type": "hypotheses",
        "payload": [x.model_dump() for x in ctx.session.state.hypotheses],
    })
    return h


@router.post("/sessions/{session_id}/hypotheses/{hypothesis_id}/investigate")
async def investigate_route(session_id: str, hypothesis_id: str, force: bool = False):
    """Run the CRAFT real-world evidence investigation (IDC + PanCancer).

    User-initiated (like enrich): streams each CRAFT tool call over WebSocket as
    an ``investigation_step`` event, then returns the updated hypothesis.
    """
    ctx = get_context(session_id)
    if not ctx:
        raise HTTPException(404, "session not ready")
    h = next((x for x in ctx.session.state.hypotheses if x.id == hypothesis_id), None)
    if not h:
        raise HTTPException(404, "hypothesis not found")
    h = await investigate_hypothesis(ctx, h, force=force)
    await ctx.session.emit({
        "type": "hypotheses",
        "payload": [x.model_dump() for x in ctx.session.state.hypotheses],
    })
    if ctx.session.state.dashboard is not None:
        await ctx.session.emit({
            "type": "dashboard",
            "payload": ctx.session.state.dashboard.model_dump(),
        })
    return h


@router.post("/sessions/{session_id}/hypotheses/{hypothesis_id}/report")
async def hypothesis_report(session_id: str, hypothesis_id: str):
    ctx = get_context(session_id)
    if not ctx:
        raise HTTPException(404, "session not ready")
    h = next((x for x in ctx.session.state.hypotheses if x.id == hypothesis_id), None)
    if not h:
        raise HTTPException(404, "hypothesis not found")
    report = await generate_report(ctx, h)
    await ctx.audit("report", "Full report generated", detail=h.statement[:60], params={"hypothesisId": hypothesis_id})
    return report


@router.post("/sessions/{session_id}/chat")
async def chat(session_id: str, req: ChatRequest):
    ctx = get_context(session_id)
    if not ctx:
        raise HTTPException(404, "session not ready")
    return await chat_agent.answer(ctx, req)


@router.post("/sessions/{session_id}/upload")
async def upload_paper(
    session_id: str,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    doi: str | None = Form(None),
):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    ctx = get_context(session_id) or make_context(session)

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "empty file")
    filename = file.filename or "upload.pdf"

    await ctx.audit("ingestion", "Uploaded PDF", detail=filename,
                    params={"bytes": len(raw)})

    text, page_count = pdf_ingest.extract_pdf(raw)
    if not text.strip():
        await ctx.audit("ingestion", "PDF extraction failed", detail=filename, status="error")
        raise HTTPException(422, "could not extract text from PDF")

    record, checksum = pdf_ingest.build_record(text, filename, title, doi)
    await ctx.audit(
        "ingestion", "Extracted text",
        detail=f"{page_count} pages · {len(text)} chars",
        params={"pages": page_count, "chars": len(text), "external_ids": record.external_ids},
    )

    # Persist original bytes + provenance for traceability.
    settings = get_settings()
    stored_path = str(Path(settings.upload_dir) / f"{record.id}.pdf")
    try:
        Path(stored_path).write_bytes(raw)
    except Exception:
        stored_path = None
    try:
        with SessionLocal() as db:
            db.add(UploadRow(
                id=uuid.uuid4().hex, session_id=session_id, paper_id=record.id,
                filename=filename, checksum=checksum, pages=page_count,
                chars=len(text), stored_path=stored_path,
            ))
            db.commit()
    except Exception:
        pass

    # First-class ingestion into the same corpus as API papers.
    session.add_papers([record])
    ingestion = IngestionAgent()
    n_chunks = await ingestion.embed_paper(ctx, record)
    await ctx.audit("ingestion", "Embedded chunks", detail=f"{n_chunks} chunks → corpus {session_id}",
                    params={"paper_id": record.id, "chunks": n_chunks, "source": "user_upload"})

    node = GraphNode(
        id=record.id, label=record.title, type="paper", source="user_pdf",
        year=record.year, summary=record.abstract[:400] or None,
        url=resolve_paper_url(record),
    )
    session.state.graph.nodes.append(node)
    await session.emit({"type": "node", "payload": node.model_dump()})

    # Reprocess so the upload joins clusters and can drive hypotheses.
    await AnalysisAgent().run(ctx)
    await GraphBuilderAgent().run(ctx)
    await ctx.audit(
        "graph_builder", "Linked upload to graph", detail=record.title[:70],
        params={"paper_id": record.id},
    )
    await after_paper_added(ctx, record)

    return {"ok": True, "paperId": record.id}
