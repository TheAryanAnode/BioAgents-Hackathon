"""Build a mini knowledge-graph slice scoped to one hypothesis."""

from __future__ import annotations

from app.agents.base import AgentContext
from app.models.schemas import GraphData, GraphLink, GraphNode


def build_hypothesis_subgraph(
    ctx: AgentContext,
    entities: list[str],
    *,
    evidence_paper_ids: list[str] | None = None,
) -> GraphData:
    """Include only the open-triangle concept nodes and papers that connect them.

    A paper is included when it mentions at least two of the hypothesis entity
    labels (the gap endpoints + bridge), or when it appears in scored evidence.
    No unrelated 1-hop neighbors are pulled in.
    """
    concept_ids: dict[str, str] = ctx.work.get("concept_ids", {})
    paper_entities: dict[str, list[str]] = ctx.work.get("paper_entities", {})
    full = ctx.session.state.graph
    if not entities:
        return GraphData()

    entity_set = {e.lower() for e in entities}
    seed_concepts: set[str] = set()
    for ent in entities:
        cid = concept_ids.get(ent)
        if cid:
            seed_concepts.add(cid)

    if not seed_concepts:
        return GraphData()

    connecting_papers: set[str] = set(evidence_paper_ids or [])
    for pid, ents in paper_entities.items():
        overlap = {e.lower() for e in ents} & entity_set
        if len(overlap) >= 2:
            connecting_papers.add(pid)

    node_ids = seed_concepts | connecting_papers
    nodes = [n for n in full.nodes if n.id in node_ids]
    links = [
        GraphLink(source=l.source, target=l.target, kind=l.kind, weight=l.weight)
        for l in full.links
        if l.source in node_ids and l.target in node_ids
    ]
    return GraphData(nodes=nodes, links=links, clusters=[])


def refresh_hypothesis_subgraphs(ctx: AgentContext) -> None:
    for h in ctx.session.state.hypotheses:
        h.subgraph = build_hypothesis_subgraph(
            ctx,
            h.entities,
            evidence_paper_ids=[e.paperId for e in h.evidence],
        )
