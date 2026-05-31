from __future__ import annotations

from itertools import combinations

from app.agents.base import AgentContext, timer
from app.agents.lexicon import ENTITY_TYPE, canon, extract_entities, is_lexicon_term
from app.models.schemas import PaperRecord


class AnalysisAgent:
    name = "analysis"

    def _entities_llm(self, ctx: AgentContext, record: PaperRecord) -> list[str] | None:
        prompt = (
            "Extract the key biomedical entities (genes, proteins, pathways, "
            "diseases, drugs) from this paper. Return JSON: "
            '{"entities": ["..."]}. Use canonical short names.\n\n'
            f"Title: {record.title}\nAbstract: {record.abstract[:1200]}"
        )
        data = ctx.llm.complete_json(prompt)
        if isinstance(data, dict) and isinstance(data.get("entities"), list):
            ents = [str(e).strip() for e in data["entities"] if str(e).strip()]
            return [canon(e) for e in ents][:8]
        return None

    async def run(self, ctx: AgentContext) -> None:
        await ctx.stage("analysis")
        papers = list(ctx.session.papers.values())
        await ctx.audit(
            self.name, "Extract entities",
            detail=f"{len(papers)} papers · {'Gemini' if ctx.llm.enabled else 'lexicon'}",
        )

        paper_entities: dict[str, list[str]] = {}
        entity_papers: dict[str, set[str]] = {}
        entity_type: dict[str, str] = {}

        with timer() as t:
            for p in papers:
                ents = None
                if ctx.llm.enabled:
                    ents = self._entities_llm(ctx, p)
                if not ents:
                    ents = extract_entities(f"{p.title}. {p.abstract}")
                paper_entities[p.id] = ents
                for e in ents:
                    entity_papers.setdefault(e, set()).add(p.id)
                    entity_type.setdefault(e, ENTITY_TYPE.get(e.lower(), "concept"))

        # Drop noisy generic concepts that appear in only one paper (lexicon
        # terms are always kept since they're domain-meaningful).
        keep = {
            e for e, pids in entity_papers.items()
            if is_lexicon_term(e) or len(pids) >= 2
        }
        if len(keep) >= 10:  # only prune when the graph stays rich enough
            entity_papers = {e: pids for e, pids in entity_papers.items() if e in keep}
            entity_type = {e: t for e, t in entity_type.items() if e in keep}
            paper_entities = {
                pid: [e for e in ents if e in keep] for pid, ents in paper_entities.items()
            }

        # Co-occurrence counts between entities (used for conceptual edges).
        cooc: dict[tuple[str, str], int] = {}
        for ents in paper_entities.values():
            for a, b in combinations(sorted(set(ents)), 2):
                cooc[(a, b)] = cooc.get((a, b), 0) + 1

        ctx.work["paper_entities"] = paper_entities
        ctx.work["entity_papers"] = {k: list(v) for k, v in entity_papers.items()}
        ctx.work["entity_type"] = entity_type
        ctx.work["cooc"] = cooc

        await ctx.audit(
            self.name, "Entities resolved",
            detail=f"{len(entity_papers)} unique concepts",
            params={
                "concepts": len(entity_papers),
                "cooccurrences": len(cooc),
            },
            duration_ms=t.elapsed_ms,
        )

        # Optional: summarize the corpus theme for richer concept tooltips.
        if ctx.llm.enabled:
            top = sorted(entity_papers.items(), key=lambda kv: len(kv[1]), reverse=True)[:6]
            ctx.work["top_concepts"] = [k for k, _ in top]
