from __future__ import annotations

from app.agents.base import AgentContext
from app.models.schemas import ChatRequest
from app.services.paper_urls import resolve_paper_url


def _session_context(ctx: AgentContext) -> str:
    hyps = ctx.session.state.hypotheses
    lines = [f"Research query: {ctx.query}"]
    if hyps:
        lines.append("Active hypotheses:")
        for i, h in enumerate(hyps[:5], 1):
            lines.append(f"  {i}. {h.statement} (confidence {h.confidence}%)")
    concept_count = sum(1 for n in ctx.session.state.graph.nodes if n.type == "concept")
    paper_count = len(ctx.session.papers)
    lines.append(f"Corpus: {paper_count} papers, {concept_count} concepts in graph.")
    return "\n".join(lines)


async def answer(ctx: AgentContext, req: ChatRequest) -> dict:
    message = req.message
    focus_label = None
    if req.focusNodeId:
        node = next(
            (n for n in ctx.session.state.graph.nodes if n.id == req.focusNodeId), None
        )
        if node:
            focus_label = node.label

    hits = ctx.vectors.search(ctx.corpus_id, message, k=8)
    citations: list[dict] = []
    seen: set[str] = set()
    context_blocks: list[str] = []

    for hit in hits:
        meta = hit["meta"]
        pid = meta.get("paper_id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        rec = ctx.session.papers.get(pid)
        title = meta.get("title", rec.title if rec else pid)
        source = meta.get("source", rec.source if rec else "derived")
        url = resolve_paper_url(rec) if rec else None
        if not url:
            node = next((n for n in ctx.session.state.graph.nodes if n.id == pid), None)
            url = node.url if node else None
        citations.append({
            "paperId": pid,
            "title": title,
            "source": source,
            "url": url,
        })
        url_note = f" ({url})" if url else ""
        context_blocks.append(f"[{title}]{url_note}\n{hit['document'][:400]}")

    await ctx.audit(
        "chat", "Retrieve evidence",
        detail=f"{len(citations)} sources · gemini={'on' if ctx.llm.enabled else 'off'}",
        params={"k": len(citations), "focus": req.focusNodeId, "message": message[:80]},
    )

    session_ctx = _session_context(ctx)
    corpus_block = "\n\n".join(context_blocks) if context_blocks else "(No closely matching papers in corpus.)"

    content = None
    if ctx.llm.enabled:
        focus_line = f"\nUser is focused on graph node: {focus_label}" if focus_label else ""
        prompt = f"""You are SynthesisOS, an expert biomedical research assistant in an autonomous literature-synthesis product.

{session_ctx}{focus_line}

INGESTED LITERATURE (prioritize when relevant — cite paper titles):
{corpus_block}

USER QUESTION:
{message}

Instructions:
1. Answer clearly in 3–8 sentences (longer if the question is complex).
2. When the question relates to the session corpus, ground your answer in the ingested literature and mention paper titles.
3. If the question is outside the corpus scope, still answer helpfully using established biomedical/scientific knowledge — prefix that portion with "General context:" so the user knows it is not from their uploaded/fetched papers.
4. If both corpus and general knowledge apply, combine them and distinguish sources.
5. Be direct; do not refuse reasonable out-of-scope questions."""
        content = ctx.llm.complete_interactive(prompt)

    if not content and ctx.llm.quota_exhausted:
        corpus_hint = ""
        if context_blocks:
            snippet = context_blocks[0].split("\n", 1)[-1][:220]
            corpus_hint = f"Based on your corpus ({len(citations)} sources): {snippet}…"
        content = (
            "Gemini rate limit reached (free tier ≈5 requests/min). "
            "Wait about a minute and try again, or set GEMINI_USE_IN_PIPELINE=false in backend/.env "
            "so the research pipeline does not consume your quota. "
            + (corpus_hint or "Try a simpler question or browse the graph and hypotheses meanwhile.")
        )

    if not content:
        if context_blocks:
            lead = context_blocks[0].split("\n", 1)[-1][:280]
            content = (
                f"From {len(citations)} papers in your corpus: {lead} "
                "Open the cited papers below for full context."
            )
        else:
            content = (
                "I couldn't find closely matching papers in this session's corpus. "
                "Try rephrasing, uploading a relevant PDF, or broadening your initial research query. "
                "Add a GOOGLE_API_KEY to enable Gemini for general biomedical Q&A beyond the corpus."
            )

    return {"content": content.strip(), "citations": citations}
