"""On-demand Gemini enrichment for a single hypothesis — one API call per click."""

from __future__ import annotations

from app.agents.base import AgentContext
from app.agents.commercial import CommercialAgent
from app.agents.evidence import EvidenceAgent, _heuristic_stance
from app.agents.subgraph import build_hypothesis_subgraph
from app.models.schemas import Hypothesis


async def enrich_hypothesis(ctx: AgentContext, h: Hypothesis) -> Hypothesis:
    """Refine statement + evidence stances with a single Gemini call. Idempotent."""
    if h.geminiEnriched or not ctx.llm.enabled:
        return h
    if not ctx.llm.can_call():
        await ctx.audit(
            "enrich",
            "Gemini skipped (rate limit)",
            detail=h.statement[:60],
            status="error",
        )
        return h

    evidence_lines = "\n".join(
        f'- paperId="{e.paperId}" title="{e.title[:90]}" snippet="{e.snippet[:140]}"'
        for e in h.evidence[:6]
    )
    entities = ", ".join(h.entities)
    prompt = f"""You are a biomedical research analyst. Refine this hypothesis and classify evidence stances.

Research domain: {ctx.query}
Current hypothesis: {h.statement}
Rationale: {h.rationale}
Gap entities: {entities}

Evidence papers:
{evidence_lines or "(no evidence yet — return empty stances array)"}

Return JSON ONLY:
{{
  "statement": "one improved testable hypothesis sentence",
  "rationale": "two sentences explaining the structural gap and mechanism",
  "stances": [{{"paperId": "...", "stance": "support|contradict|neutral"}}]
}}"""

    data = ctx.llm.complete_json_interactive(prompt)
    if not isinstance(data, dict):
        await ctx.audit(
            "enrich",
            "Gemini enrichment unavailable",
            detail=h.statement[:60],
            status="error",
        )
        return h

    if data.get("statement"):
        h.statement = str(data["statement"]).strip()[:500]
    if data.get("rationale"):
        h.rationale = str(data["rationale"]).strip()[:800]

    stance_map: dict[str, str] = {}
    for item in data.get("stances") or []:
        if isinstance(item, dict) and item.get("paperId") and item.get("stance") in (
            "support",
            "contradict",
            "neutral",
        ):
            stance_map[str(item["paperId"])] = item["stance"]

    agent = EvidenceAgent()
    for e in h.evidence:
        if e.paperId in stance_map:
            e.stance = stance_map[e.paperId]  # type: ignore[assignment]
        else:
            rec = ctx.session.papers.get(e.paperId)
            full_text = f"{rec.title} {rec.abstract}" if rec else e.snippet
            stance, blended = _heuristic_stance(h.entities, full_text, e.relevance)
            e.stance = stance  # type: ignore[assignment]
            e.relevance = round(blended, 3)

    score, breakdown = agent._score_detail(h.evidence)
    h.confidence = score
    h.confidenceBreakdown = breakdown
    h.confidenceExplanation = agent._confidence_explanation(h, breakdown, score)
    h.history = agent._history(ctx, h.evidence, h.confidence)
    support = breakdown.supportCount
    contradict = breakdown.contradictCount
    h.status = (
        "contested"
        if contradict >= support and contradict > 0
        else ("supported" if h.confidence >= 70 else "emerging")
    )
    h.subgraph = build_hypothesis_subgraph(
        ctx, h.entities, evidence_paper_ids=[e.paperId for e in h.evidence]
    )
    CommercialAgent().attach_opportunity(ctx, h)
    h.geminiEnriched = True

    await ctx.audit(
        "enrich",
        "Hypothesis enriched (Gemini)",
        detail=h.statement[:80],
        params={"hypothesisId": h.id, "confidence": h.confidence},
    )
    return h
