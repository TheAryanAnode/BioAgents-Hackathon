from __future__ import annotations

import asyncio
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
from app.agents.orchestrator import get_context, make_context, run_pipeline
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
from app.services.session_store import store

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok", "gemini": get_llm().enabled}


@router.post("/research")
async def start_research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "query is required")
    session_id = uuid.uuid4().hex[:12]
    session = store.create(session_id, req.query.strip())
    # Kick off the pipeline in the background; the client streams via WebSocket.
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
    ctx.session.state.hypotheses.append(h)
    await ctx.audit("hypothesis", "Manual hypothesis added", detail=h.statement[:80])
    return h


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
    )
    session.state.graph.nodes.append(node)
    await session.emit({"type": "node", "payload": node.model_dump()})

    # Reprocess so the upload joins clusters and can serve as evidence.
    await AnalysisAgent().run(ctx)
    await GraphBuilderAgent().run(ctx)
    await ctx.audit("graph_builder", "Linked upload to graph", detail=record.title[:70],
                    params={"paper_id": record.id})
    if session.state.hypotheses:
        await EvidenceAgent().run(ctx)
        await CommercialAgent().run(ctx)

    return {"ok": True, "paperId": record.id}
