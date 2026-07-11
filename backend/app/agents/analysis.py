from __future__ import annotations

import re
from itertools import combinations

from app.agents.base import AgentContext, timer
from app.agents.lexicon import (
    ENTITY_TYPE,
    canon,
    extract_entities,
    guess_type,
    is_lexicon_term,
)
from app.models.schemas import PaperRecord


def parse_query_terms(query: str) -> list[str]:
    """Split a free-text / boolean query into clean concept phrases.

    Handles ``asthma AND lung cancer``, ``"tau propagation" OR amyloid``,
    ``crispr, base editing`` etc. Boolean operators, quotes and punctuation are
    stripped so each side becomes a seed concept that anchors the graph.
    """
    q = query.strip()
    # Split on boolean operators (word-boundaried, case-insensitive) and commas/;.
    parts = re.split(r"\b(?:and|or|not|vs\.?|versus)\b|[,;/]+", q, flags=re.IGNORECASE)
    terms: list[str] = []
    seen: set[str] = set()
    for p in parts:
        p = p.strip().strip('"\'()')
        p = re.sub(r"\s+", " ", p)
        if len(p) < 3:
            continue
        # Title-case for display, preserving acronyms/genes.
        disp = " ".join(w if w.isupper() else w.capitalize() for w in p.split())
        if disp.lower() not in seen:
            seen.add(disp.lower())
            terms.append(disp)
    # Fallback: if parsing produced nothing, use the whole cleaned query.
    if not terms and len(q) >= 3:
        terms.append(q.title())
    return terms[:4]


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
            detail=f"{len(papers)} papers · {'Nebius (pipeline)' if ctx.llm.pipeline_llm_allowed else 'lexicon'}",
        )

        paper_entities: dict[str, list[str]] = {}
        entity_papers: dict[str, set[str]] = {}
        entity_type: dict[str, str] = {}

        # Query terms are guaranteed concepts so the searched topic always
        # anchors the graph (e.g. "asthma AND lung cancer" -> Asthma, Lung Cancer).
        query_terms = parse_query_terms(ctx.query)
        ctx.work["query_terms"] = query_terms
        query_lc = {t.lower(): t for t in query_terms}

        with timer() as t:
            for p in papers:
                # Entity extraction uses the domain-agnostic lexicon — no LLM spend.
                ents = extract_entities(f"{p.title}. {p.abstract}")
                blob = f"{p.title}. {p.abstract}".lower()
                # Attribute any query term that literally appears in the paper.
                for lc, disp in query_lc.items():
                    if lc in blob and disp not in ents:
                        ents.insert(0, disp)
                paper_entities[p.id] = ents
                for e in ents:
                    entity_papers.setdefault(e, set()).add(p.id)
                    entity_type.setdefault(e, guess_type(e))

        # Guarantee every query term is a hub: if it wasn't found in enough
        # abstracts, attach it to the earliest papers so it survives pruning and
        # links the corpus together.
        for disp in query_terms:
            pids = entity_papers.setdefault(disp, set())
            entity_type.setdefault(disp, guess_type(disp))
            if len(pids) < 2:
                for p in papers[: max(3, len(papers) // 4)]:
                    pids.add(p.id)
                    if disp not in paper_entities.get(p.id, []):
                        paper_entities.setdefault(p.id, []).append(disp)

        # Drop noisy generic concepts that appear in only one paper (lexicon
        # terms, query terms, and user uploads are always kept).
        user_paper_ids = {p.id for p in papers if p.source == "user_pdf"}
        query_set = {t.lower() for t in query_terms}
        keep = {
            e for e, pids in entity_papers.items()
            if is_lexicon_term(e)
            or e.lower() in query_set
            or len(pids) >= 2
            or any(pid in user_paper_ids for pid in pids)
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
