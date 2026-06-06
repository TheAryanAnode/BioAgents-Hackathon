from __future__ import annotations

import hashlib

from app.agents.base import AgentContext, timer
from app.models.schemas import (
    DashboardData,
    DashboardMetrics,
    Hypothesis,
    HypothesisOpportunity,
    Opportunity,
    RoiBreakdown,
)


def _stable_int(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


class CommercialAgent:
    name = "commercial"

    def attach_opportunity(self, ctx: AgentContext, h: Hypothesis) -> HypothesisOpportunity:
        opp = self._hypothesis_opportunity(ctx, h)
        h.opportunity = opp
        return opp

    def _hypothesis_opportunity(self, ctx: AgentContext, h: Hypothesis) -> HypothesisOpportunity:
        ents = h.entities or [ctx.query]
        subgroup = " + ".join(dict.fromkeys([e for e in ents if e]))[:60] or ctx.query
        population = _stable_int(h.id + "pop", 8_000, 480_000)
        competition = {"emerging": 22, "supported": 48, "contested": 35}.get(h.status, 40)
        competition = max(5, min(95, competition + _stable_int(h.id + "c", -8, 8)))
        unmet = max(20, min(98, h.confidence + _stable_int(h.id + "u", 5, 25)))
        whitespace = 100 - competition

        conf_comp = int(round(0.4 * h.confidence))
        unmet_comp = int(round(0.3 * unmet))
        ws_comp = int(round(0.3 * whitespace))
        roi = max(5, min(98, conf_comp + unmet_comp + ws_comp))

        roi_rationale = (
            f"ROI score {roi}/100 = 40% of hypothesis confidence ({h.confidence} → +{conf_comp}) "
            f"+ 30% unmet need ({unmet} → +{unmet_comp}) "
            f"+ 30% competitive whitespace ({whitespace} → +{ws_comp}). "
            f"Targets ~{population:,} patients in the {subgroup} subgroup."
        )

        rationale = (
            f"Targets the {subgroup} subgroup. Confidence {h.confidence}% with "
            f"{whitespace}/100 competitive whitespace suggests an under-served "
            f"opportunity of ~{population:,} patients."
        )
        if ctx.llm.pipeline_llm_allowed:
            text = ctx.llm.complete(
                "In one sentence, give the commercial rationale for pursuing this "
                f"hypothesis as a drug-development opportunity: {h.statement}"
            )
            if text:
                rationale = text.strip()[:300]

        funding = 250_000 + min(population // 50, 3_500_000) + unmet * 8_000

        return HypothesisOpportunity(
            id=f"opp_{h.id}",
            hypothesisId=h.id,
            title=f"{ents[0]} → {ents[-1]}" if len(ents) >= 2 else (ents[0] if ents else ctx.query),
            subgroup=subgroup,
            patientPopulation=population,
            unmetNeed=unmet,
            competition=competition,
            roiScore=roi,
            rationale=rationale,
            roiRationale=roi_rationale,
            roiBreakdown=RoiBreakdown(
                confidenceComponent=conf_comp,
                unmetNeedComponent=unmet_comp,
                whitespaceComponent=ws_comp,
            ),
            estimatedFundingUsd=int(funding),
            whitespace=whitespace,
        )

    def _opportunity(self, ctx: AgentContext, h: Hypothesis) -> Opportunity:
        ho = h.opportunity or self._hypothesis_opportunity(ctx, h)
        return Opportunity(
            id=ho.id,
            hypothesisId=ho.hypothesisId,
            title=ho.title,
            subgroup=ho.subgroup,
            patientPopulation=ho.patientPopulation,
            unmetNeed=ho.unmetNeed,
            competition=ho.competition,
            roiScore=ho.roiScore,
            rationale=ho.rationale,
        )

    def _trends(self, ctx: AgentContext) -> tuple[list[dict], list[str]]:
        entity_papers: dict[str, list[str]] = ctx.work.get("entity_papers", {})
        papers = ctx.session.papers
        top = sorted(entity_papers.items(), key=lambda kv: len(kv[1]), reverse=True)[:4]
        topics = [t for t, _ in top]
        years = sorted({p.year for p in papers.values() if p.year})
        if not years:
            years = list(range(2016, 2025))
        years = [y for y in years if y >= years[-1] - 9] if len(years) > 9 else years
        rows = []
        for y in years:
            row: dict = {"year": y}
            for topic, pids in top:
                count = sum(
                    1 for pid in pids if (papers.get(pid) and papers[pid].year and papers[pid].year <= y)
                )
                row[topic] = count
            rows.append(row)
        return rows, topics

    def _stratification(self, opps: list[HypothesisOpportunity]) -> list[dict]:
        return [
            {"subgroup": o.subgroup[:24], "prevalence": min(100, int(o.patientPopulation / 5000))}
            for o in opps
        ][:6]

    def _cross_disease(self, ctx: AgentContext) -> list[dict]:
        cooc: dict[tuple[str, str], int] = ctx.work.get("cooc", {})
        entity_type: dict[str, str] = ctx.work.get("entity_type", {})
        out = []
        for (a, b), w in sorted(cooc.items(), key=lambda x: x[1], reverse=True):
            if entity_type.get(a) == "disease" and entity_type.get(b) == "disease":
                out.append({"from": a, "to": b, "strength": w})
        return out[:8]

    async def run(self, ctx: AgentContext) -> DashboardData:
        await ctx.stage("commercial")
        hyps = ctx.session.state.hypotheses
        with timer() as t:
            opps = [self.attach_opportunity(ctx, h) for h in hyps]
            trends, topics = self._trends(ctx)
            strat = self._stratification(opps)
            cross = self._cross_disease(ctx)

        avg_conf = int(round(sum(h.confidence for h in hyps) / max(1, len(hyps))))
        total_pop = sum(o.patientPopulation for o in opps)
        avg_roi = round(sum(o.roiScore for o in opps) / max(1, len(opps)) / 20, 1)

        dashboard = DashboardData(
            metrics=DashboardMetrics(
                opportunities=len(opps),
                avgConfidence=avg_conf,
                patientPopulation=total_pop,
                projectedRoi=avg_roi,
            ),
            opportunities=[self._opportunity(ctx, h) for h in hyps],
            trends=trends,
            trendTopics=topics,
            stratification=strat,
            crossDisease=cross,
        )
        ctx.session.state.dashboard = dashboard
        await ctx.session.emit({"type": "hypotheses", "payload": [h.model_dump() for h in hyps]})
        await ctx.session.emit({"type": "dashboard", "payload": dashboard.model_dump()})
        await ctx.audit(
            self.name, "Commercial analysis complete",
            detail=f"{len(opps)} opportunities embedded in hypotheses",
            params={"opportunities": len(opps), "avg_confidence": avg_conf},
            duration_ms=t.elapsed_ms,
        )
        return dashboard
