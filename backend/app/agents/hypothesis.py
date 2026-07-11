from __future__ import annotations

import uuid

import networkx as nx

from app.agents.base import AgentContext, timer
from app.agents.subgraph import build_hypothesis_subgraph
from app.models.schemas import Hypothesis


def _open_triangles(
    g: nx.Graph,
    concept_ids: dict[str, str],
    entity_type: dict[str, str],
    topic: str,
) -> list[tuple[str, str, str, int]]:
    """Find (a, b, bridge, score) where concepts a and b share neighbors but are
    not directly connected — a structural gap / candidate novel link. Prefers
    mechanistic bridges (gene/pathway) over the dominant topic hub, and prefers
    endpoint pairs that span different clusters."""
    concept_nodes = [cid for cid in concept_ids.values() if g.has_node(cid)]
    topic_l = topic.lower()

    def kind(node: str) -> str:
        return entity_type.get(g.nodes[node].get("label", ""), "concept")

    def is_topic(node: str) -> bool:
        return g.nodes[node].get("label", "").lower() in topic_l or topic_l in g.nodes[node].get("label", "").lower()

    gaps: list[tuple[str, str, str, int]] = []
    for i in range(len(concept_nodes)):
        for j in range(i + 1, len(concept_nodes)):
            a, b = concept_nodes[i], concept_nodes[j]
            if g.has_edge(a, b):
                continue
            if is_topic(a) or is_topic(b):
                continue  # endpoints should be specific, not the search topic
            common = set(g.neighbors(a)) & set(g.neighbors(b))
            common_concepts = [c for c in common if g.nodes[c].get("type") == "concept"]
            if not common_concepts:
                continue
            # Prefer a mechanistic, non-topic bridge.
            def bridge_pref(c: str) -> tuple[int, int]:
                mech = 2 if kind(c) in ("pathway", "gene") else (0 if is_topic(c) else 1)
                return (mech, g.degree(c))
            bridge = max(common_concepts, key=bridge_pref)
            cross_cluster = 1 if g.nodes[a].get("cluster") != g.nodes[b].get("cluster") else 0
            endpoint_quality = sum(1 for n in (a, b) if kind(n) in ("gene", "pathway", "disease"))
            score = (
                len(common) * (g.degree(a) + g.degree(b))
                + cross_cluster * 25
                + endpoint_quality * 15
                + (10 if kind(bridge) in ("pathway", "gene") else 0)
            )
            gaps.append((a, b, bridge, score))
    gaps.sort(key=lambda x: x[3], reverse=True)
    return gaps


def _label(g: nx.Graph, node: str) -> str:
    return g.nodes[node].get("label", node)


class HypothesisAgent:
    name = "hypothesis"

    def _statement_llm(self, ctx: AgentContext, a: str, b: str, bridge: str) -> dict | None:
        prompt = (
            "You are a biomedical research strategist. Given a knowledge-graph "
            f"gap, propose ONE novel, testable hypothesis linking '{a}' and '{b}' "
            f"(they co-occur with '{bridge}' but are never directly connected in the "
            "literature). Return JSON: {\"statement\": \"...\", \"rationale\": \"...\"}. "
            "Keep the statement to one sentence; rationale to two sentences."
        )
        data = ctx.llm.complete_json(prompt)
        if isinstance(data, dict) and data.get("statement"):
            return data
        return None

    def _build(self, ctx: AgentContext, a: str, b: str, bridge: str) -> Hypothesis:
        # Heuristic only — Gemini runs on explicit hypothesis click (enrich endpoint).
        statement = (
            f"{a} contributes to {b} through {bridge}, a connection not yet "
            f"directly established in the literature."
        )
        rationale = (
            f"Both {a} and {b} co-occur with {bridge} across the corpus, yet no "
            f"paper directly links {a} to {b}. This open triangle suggests {bridge} "
            f"may be the mechanistic bridge between them."
        )
        entities = [a, bridge, b]
        concept_ids: dict[str, str] = ctx.work.get("concept_ids", {})
        gap_ids = [concept_ids[e] for e in entities if concept_ids.get(e)]
        h = Hypothesis(
            id=str(uuid.uuid4())[:8],
            statement=statement,
            rationale=rationale,
            confidence=50,
            status="emerging",
            evidence=[],
            history=[],
            entities=entities,
            gapNodeIds=gap_ids,
        )
        h.subgraph = build_hypothesis_subgraph(ctx, entities)
        return h

    def _fallback_gaps(
        self, g: nx.Graph, concept_ids: dict[str, str], entity_type: dict[str, str], topic: str
    ) -> list[tuple[str, str, str]]:
        """When no clean open triangles exist (sparse graph / unusual topic),
        still propose hypotheses by pairing the most connected specific concepts,
        bridged by a shared neighbor or the dominant topic hub. Guarantees the
        product returns hypotheses for ANY searched topic."""
        topic_l = topic.lower()
        nodes = [cid for cid in concept_ids.values() if g.has_node(cid)]
        if len(nodes) < 2:
            return []

        def label(n: str) -> str:
            return g.nodes[n].get("label", n)

        def is_topic(n: str) -> bool:
            lab = label(n).lower()
            return lab in topic_l or topic_l in lab

        # Rank specific (non-topic) concepts by degree; prefer gene/pathway/disease.
        def rank(n: str) -> tuple[int, int]:
            k = entity_type.get(label(n), "concept")
            mech = 1 if k in ("gene", "pathway", "disease", "drug") else 0
            return (mech, g.degree(n))

        specific = sorted((n for n in nodes if not is_topic(n)), key=rank, reverse=True)
        topic_nodes = [n for n in nodes if is_topic(n)]
        default_bridge = topic_nodes[0] if topic_nodes else (specific[-1] if specific else None)

        out: list[tuple[str, str, str]] = []
        seen: set[frozenset] = set()
        for i in range(len(specific)):
            for j in range(i + 1, len(specific)):
                a, b = specific[i], specific[j]
                if g.has_edge(a, b):
                    continue
                key = frozenset([a, b])
                if key in seen:
                    continue
                seen.add(key)
                shared = set(g.neighbors(a)) & set(g.neighbors(b))
                shared_concepts = [c for c in shared if g.nodes[c].get("type") == "concept"]
                bridge = shared_concepts[0] if shared_concepts else default_bridge
                if bridge is None or bridge in (a, b):
                    continue
                out.append((label(a), label(b), label(bridge)))
                if len(out) >= 8:
                    return out
        return out

    def candidate_gaps(self, ctx: AgentContext):
        g: nx.Graph = ctx.work.get("nx_graph")
        concept_ids: dict[str, str] = ctx.work.get("concept_ids", {})
        entity_type: dict[str, str] = ctx.work.get("entity_type", {})
        if g is None or not concept_ids:
            return []
        gaps = _open_triangles(g, concept_ids, entity_type, ctx.query)
        result = [(_label(g, a), _label(g, b), _label(g, bridge)) for a, b, bridge, _ in gaps]
        if len(result) < 3:
            # Sparse graph — supplement with degree-based fallback pairs.
            existing = {frozenset([a, b]) for a, b, _ in result}
            for a, b, bridge in self._fallback_gaps(g, concept_ids, entity_type, ctx.query):
                if frozenset([a, b]) not in existing:
                    result.append((a, b, bridge))
        return result

    async def run(self, ctx: AgentContext, n: int = 3) -> list[Hypothesis]:
        await ctx.stage("hypothesis")
        with timer() as t:
            gaps = self.candidate_gaps(ctx)
        await ctx.audit(
            self.name, "Scan for structural gaps",
            detail=f"{len(gaps)} candidate open triangles",
            params={"candidates": len(gaps)}, duration_ms=t.elapsed_ms,
        )

        hyps: list[Hypothesis] = []
        used: set[frozenset] = set()
        for a, b, bridge in gaps:
            key = frozenset([a, b])
            if key in used:
                continue
            used.add(key)
            h = self._build(ctx, a, b, bridge)
            hyps.append(h)
            await ctx.audit(
                self.name, "Hypothesis generated",
                detail=h.statement[:90],
                params={"entities": h.entities},
            )
            if len(hyps) >= n:
                break

        ctx.session.state.hypotheses = hyps
        ctx.work["hypothesis_agent"] = self
        return hyps

    async def propose_one(self, ctx: AgentContext) -> Hypothesis:
        """On-demand generation for the 'Generate' button — picks the next
        unused gap."""
        existing = {frozenset(h.entities[::2]) for h in ctx.session.state.hypotheses}
        for a, b, bridge in self.candidate_gaps(ctx):
            if frozenset([a, b]) not in existing:
                h = self._build(ctx, a, b, bridge)
                await ctx.audit(self.name, "Hypothesis generated (on demand)", detail=h.statement[:90])
                return h
        # Fall back to a fresh combination if all gaps exhausted.
        gaps = self.candidate_gaps(ctx)
        if gaps:
            a, b, bridge = gaps[0]
            return self._build(ctx, a, b, bridge)
        return Hypothesis(
            id=str(uuid.uuid4())[:8],
            statement="Insufficient graph structure to derive a new hypothesis.",
            rationale="Ingest more literature to expand the concept network.",
            confidence=20, status="emerging", evidence=[], history=[], entities=[],
        )
