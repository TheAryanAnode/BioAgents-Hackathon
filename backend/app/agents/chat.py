from __future__ import annotations

from app.agents.base import AgentContext
from app.models.schemas import ChatRequest


async def answer(ctx: AgentContext, req: ChatRequest) -> dict:
    query = req.message
    if req.focusNodeId:
        node = next(
            (n for n in ctx.session.state.graph.nodes if n.id == req.focusNodeId), None
        )
        if node:
            query = f"{req.message} (context: {node.label})"

    hits = ctx.vectors.search(ctx.corpus_id, query, k=6)
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
        citations.append({"paperId": pid, "title": title, "source": source})
        context_blocks.append(f"[{title}] {hit['document'][:300]}")

    await ctx.audit(
        "chat", "Retrieve evidence",
        detail=f"{len(citations)} sources for: {req.message[:50]}",
        params={"k": len(citations), "focus": req.focusNodeId},
    )

    content = None
    if ctx.llm.enabled and context_blocks:
        prompt = (
            "You are SynthesisOS, a biomedical research assistant. Answer the "
            "question using ONLY the provided sources. Be concise (3-5 sentences) "
            "and reference findings naturally.\n\n"
            f"Question: {req.message}\n\nSources:\n" + "\n\n".join(context_blocks)
        )
        content = ctx.llm.complete(prompt)

    if not content:
        if context_blocks:
            lead = context_blocks[0].split("] ", 1)[-1]
            content = (
                f"Based on {len(citations)} sources in the current corpus: {lead} "
                f"The synthesized literature connects this to {', '.join(c['title'][:40] for c in citations[1:3])}. "
                "See the cited papers for detail."
            )
        else:
            content = (
                "I don't have enough ingested literature to answer that yet. "
                "Try broadening the query or uploading a relevant paper."
            )

    return {"content": content, "citations": citations}
