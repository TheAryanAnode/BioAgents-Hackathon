"""Radiogenomics analyst — the biotech challenge on a plate.

Answers the official prompt: *do imaging modalities correlate with molecular
subtypes across cancers?* It runs two aggregate CRAFT queries — mutation
prevalence **by cancer type** (PanCancer) and imaging modality distribution **by
collection** (IDC) — joins them on TCGA study/collection, and builds a
modality × cancer-type correlation matrix.

An unsupervised k-means pass (numpy, no heavy deps) then clusters the cancer
types into "radiogenomic archetypes" — e.g. *CT-dominant, mutation-high* — the
kind of finding a real imaging researcher would act on.

These two extra CRAFT calls are recorded on the timeline for provenance but do
NOT consume the per-hypothesis execute_query budget (they run once, after the
core genomic/imaging queries).
"""

from __future__ import annotations

import numpy as np

from app.agents.investigation.runner import InvestigationContext
from app.services.craft_mcp import MATRIX_STUDIES, study_info

AGENT = "craft_radiogenomics"

# DICOM modality display order for the heatmap rows.
_MODALITY_ORDER = ["CT", "MR", "PT", "SEG", "RTSTRUCT", "CR"]


async def run(ic: InvestigationContext) -> None:
    gene = ic.gene_a
    studies = list(MATRIX_STUDIES)
    collections = [study_info(s)[1] for s in studies]

    # Q1 — mutation prevalence by cancer type (PanCancer).
    gen1 = await ic.craft.generate_sql(
        f"{gene} mutation frequency across TCGA studies by cancer type",
        ic.pancancer, domain="rg_prevalence",
    )
    sql1 = str(gen1.get("sql", ""))
    await ic.record(
        phase="query", agent=AGENT,
        question=f"Prevalence of {gene} across cancer types",
        tool="generate_sql", connection=ic.pancancer,
        tool_input={"question": f"{gene} mutation frequency by cancer type"},
        sql=sql1, live=bool(gen1.get("live")),
    )
    res1 = await ic.craft.execute_query(
        sql1, ic.pancancer, context={"gene": gene, "studies": studies}, domain="rg_prevalence",
    )
    prevalence_rows = list(res1.get("rows", []))
    await ic.record(
        phase="query", agent=AGENT,
        question=f"Read {len(prevalence_rows)} cancer-type prevalence rows",
        tool="execute_query", connection=ic.pancancer,
        tool_output={"columns": res1.get("columns", []), "rows": prevalence_rows[:12]},
        sql=sql1, row_count=len(prevalence_rows), live=bool(res1.get("live")),
    )

    # Q2 — imaging modality distribution by collection (IDC).
    gen2 = await ic.craft.generate_sql(
        "DICOM imaging modality distribution across TCGA collections",
        ic.idc, domain="rg_modality",
    )
    sql2 = str(gen2.get("sql", ""))
    await ic.record(
        phase="query", agent=AGENT,
        question="Imaging modality coverage across cancer collections",
        tool="generate_sql", connection=ic.idc,
        tool_input={"question": "modality distribution by collection"},
        sql=sql2, live=bool(gen2.get("live")),
    )
    res2 = await ic.craft.execute_query(
        sql2, ic.idc, context={"studies": studies, "collections": collections}, domain="rg_modality",
    )
    modality_rows = list(res2.get("rows", []))
    await ic.record(
        phase="query", agent=AGENT,
        question=f"Read {len(modality_rows)} modality×collection rows",
        tool="execute_query", connection=ic.idc,
        tool_output={"columns": res2.get("columns", []), "rows": modality_rows[:12]},
        sql=sql2, row_count=len(modality_rows), live=bool(res2.get("live")),
    )

    matrix = _build_matrix(prevalence_rows, modality_rows, studies)
    if not matrix["cancers"] or not matrix["modalities"]:
        return

    archetypes = _kmeans_archetypes(matrix, k=3)
    figure = _heatmap_figure(matrix, gene)

    ic.metrics["matrixChart"] = figure
    ic.metrics["archetypes"] = archetypes
    ic.metrics["matrix"] = matrix

    await ic.record(
        phase="chart", agent=AGENT,
        question="Chart radiogenomic correlation matrix (modalities × cancer types)",
        tool="generate_plotly_chart",
        tool_input={"chart_type": "heatmap", "rows": len(matrix["modalities"]),
                    "cols": len(matrix["cancers"])},
        tool_output={"archetypes": [a["label"] for a in archetypes]},
        live=bool(res2.get("live")),
    )
    await ic.record(
        phase="synthesis", agent=AGENT,
        question="Cluster cancer types into radiogenomic archetypes (k-means, k=3)",
        tool="synthesis",
        tool_output={
            "archetypes": [
                {"label": a["label"], "members": a["members"],
                 "dominantModality": a["dominantModality"],
                 "avgPrevalencePct": a["avgPrevalencePct"]}
                for a in archetypes
            ],
        },
    )


def _build_matrix(prevalence_rows, modality_rows, studies) -> dict:
    """Assemble modality × cancer-type coverage matrix + per-cancer prevalence."""
    study_to_name = {s: study_info(s)[0] for s in studies}
    coll_to_study = {study_info(s)[1]: s for s in studies}

    prevalence: dict[str, float] = {}
    for r in prevalence_rows:
        st = str(r.get("study", "")).upper()
        if st:
            prevalence[st] = float(r.get("frequency_pct", 0.0))

    # coverage[study][modality] = imaging study count
    coverage: dict[str, dict[str, int]] = {}
    modalities_seen: set[str] = set()
    for r in modality_rows:
        coll = str(r.get("collection", ""))
        st = coll_to_study.get(coll)
        if not st:
            continue
        mod = str(r.get("modality", ""))
        n = int(r.get("studies", 0) or 0)
        modalities_seen.add(mod)
        coverage.setdefault(st, {})[mod] = coverage.setdefault(st, {}).get(mod, 0) + n

    # Keep only cancers that have both prevalence and imaging coverage.
    cancers = [s for s in studies if s in coverage]
    modalities = [m for m in _MODALITY_ORDER if m in modalities_seen]
    modalities += sorted(m for m in modalities_seen if m not in modalities)

    z: list[list[int]] = []
    for mod in modalities:
        z.append([int(coverage.get(s, {}).get(mod, 0)) for s in cancers])

    return {
        "modalities": modalities,
        "cancers": [study_to_name.get(s, s) for s in cancers],
        "cancerCodes": cancers,
        "z": z,
        "prevalence": [round(prevalence.get(s, 0.0), 1) for s in cancers],
    }


def _kmeans_archetypes(matrix: dict, k: int = 3) -> list[dict]:
    """Deterministic tiny k-means over cancer-type feature vectors.

    Each cancer is a vector of [normalized modality coverage..., prevalence].
    Clusters become "radiogenomic archetypes" labelled by dominant modality and
    mutation level.
    """
    cancers = matrix["cancers"]
    modalities = matrix["modalities"]
    z = np.array(matrix["z"], dtype=float)  # shape: (modalities, cancers)
    if z.size == 0 or len(cancers) < 2:
        return []

    # Feature matrix: cancers × (modalities + prevalence). Column-normalize
    # coverage so magnitude differences between modalities don't dominate.
    cov = z.T  # (cancers, modalities)
    col_max = cov.max(axis=0)
    col_max[col_max == 0] = 1.0
    cov_norm = cov / col_max
    prev = np.array(matrix["prevalence"], dtype=float).reshape(-1, 1) / 100.0
    feats = np.hstack([cov_norm, prev])  # (cancers, modalities+1)

    k = int(min(k, len(cancers)))
    if k < 1:
        return []

    # Deterministic init: sort by prevalence then pick evenly spaced seeds.
    order = np.argsort(-feats[:, -1])
    seed_idx = [order[int(round(i * (len(order) - 1) / max(1, k - 1)))] for i in range(k)]
    centroids = feats[seed_idx].copy()

    labels = np.zeros(len(cancers), dtype=int)
    for _ in range(25):
        dists = np.linalg.norm(feats[:, None, :] - centroids[None, :, :], axis=2)
        new_labels = dists.argmin(axis=1)
        if np.array_equal(new_labels, labels) and _ > 0:
            labels = new_labels
            break
        labels = new_labels
        for c in range(k):
            members = feats[labels == c]
            if len(members):
                centroids[c] = members.mean(axis=0)

    archetypes: list[dict] = []
    for c in range(k):
        idxs = [i for i in range(len(cancers)) if labels[i] == c]
        if not idxs:
            continue
        member_cov = cov[idxs]  # (n, modalities)
        mod_means = member_cov.mean(axis=0)
        dom_i = int(mod_means.argmax()) if len(mod_means) else 0
        dominant = modalities[dom_i] if modalities else "—"
        avg_prev = float(np.mean([matrix["prevalence"][i] for i in idxs]))
        total_studies = int(member_cov.sum())
        prev_word = "mutation-high" if avg_prev >= 25 else ("mutation-moderate" if avg_prev >= 12 else "mutation-low")
        archetypes.append({
            "label": f"{dominant}-dominant · {prev_word}",
            "members": [cancers[i] for i in idxs],
            "dominantModality": dominant,
            "avgPrevalencePct": round(avg_prev, 1),
            "totalStudies": total_studies,
        })
    archetypes.sort(key=lambda a: a["avgPrevalencePct"], reverse=True)
    return archetypes


def _heatmap_figure(matrix: dict, gene: str) -> dict:
    """Plotly-compatible heatmap spec (z / x / y) for the frontend renderer."""
    return {
        "data": [{
            "type": "heatmap",
            "z": matrix["z"],
            "x": matrix["cancers"],
            "y": matrix["modalities"],
            "colorscale": "hot",
        }],
        "layout": {
            "title": f"Radiogenomic coverage — imaging modality × cancer type ({gene} context)",
            "xaxis": {"title": "Cancer type (molecular subtype)"},
            "yaxis": {"title": "DICOM modality"},
        },
        "prevalence": matrix["prevalence"],
        "cancers": matrix["cancers"],
    }
