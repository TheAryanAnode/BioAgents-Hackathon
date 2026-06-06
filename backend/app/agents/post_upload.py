"""Reconcile graph, hypotheses, and evidence after a user PDF upload."""

from __future__ import annotations

from app.agents.base import AgentContext
from app.agents.commercial import CommercialAgent
from app.agents.evidence import EvidenceAgent
from app.agents.hypothesis import HypothesisAgent
from app.agents.subgraph import refresh_hypothesis_subgraphs
from app.models.schemas import PaperRecord


async def after_paper_added(ctx: AgentContext, record: PaperRecord) -> None:
    """Ensure uploads join the graph and can drive or strengthen hypotheses."""
    upload_ents = set(ctx.work.get("paper_entities", {}).get(record.id, []))
    hyp_agent = HypothesisAgent()
    existing_pairs = {frozenset([h.entities[0], h.entities[2]]) for h in ctx.session.state.hypotheses if len(h.entities) >= 3}

    # New structural gap involving this upload's entities.
    for a, b, bridge in hyp_agent.candidate_gaps(ctx):
        triangle = {a, b, bridge}
        if len(triangle & upload_ents) >= 2 and frozenset([a, b]) not in existing_pairs:
            h = hyp_agent._build(ctx, a, b, bridge)
            ctx.session.state.hypotheses.append(h)
            existing_pairs.add(frozenset([a, b]))
            await ctx.audit(
                "hypothesis",
                "Upload triggered hypothesis",
                detail=h.statement[:90],
                params={"paper_id": record.id, "entities": h.entities},
            )
            break

    if not ctx.session.state.hypotheses:
        hyps = await hyp_agent.run(ctx, n=3)
        if hyps:
            await ctx.session.emit({"type": "hypotheses", "payload": [h.model_dump() for h in hyps]})

    if ctx.session.state.hypotheses:
        await EvidenceAgent().run(ctx)
        refresh_hypothesis_subgraphs(ctx)
        await CommercialAgent().run(ctx)
        await ctx.session.emit({
            "type": "hypotheses",
            "payload": [h.model_dump() for h in ctx.session.state.hypotheses],
        })
