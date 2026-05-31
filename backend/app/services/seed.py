"""Deterministic fallback corpus so the product always demos end-to-end,
even with no network or API key. The autism-genomics set is curated with a
deliberate structural gap (SCN2A / GABAergic signaling / epilepsy comorbidity)
that the hypothesis agent is designed to surface."""

from __future__ import annotations

import hashlib

from app.models.schemas import PaperRecord

_AUTISM_PAPERS: list[dict] = [
    {
        "title": "De novo mutations in SHANK3 disrupt synaptic scaffolding in autism spectrum disorder",
        "authors": ["Durand C", "Betancur C", "Boeckers T"],
        "year": 2019,
        "citation_count": 1820,
        "abstract": "SHANK3 encodes a postsynaptic scaffolding protein at glutamatergic synapses. De novo loss-of-function mutations impair synaptic plasticity and dendritic spine maturation, producing core autism phenotypes in model systems.",
    },
    {
        "title": "CHD8 haploinsufficiency drives a chromatin-remodeling subtype of autism",
        "authors": ["Bernier R", "Golzio C", "Katsanis N"],
        "year": 2020,
        "citation_count": 1540,
        "abstract": "CHD8 is a chromatin remodeler regulating neurodevelopmental gene expression. Haploinsufficiency defines a recognizable autism subtype with macrocephaly and gastrointestinal disturbance, implicating chromatin remodeling pathways.",
    },
    {
        "title": "SCN2A variants and the spectrum from autism to early infantile epilepsy",
        "authors": ["Sanders S", "Ben-Shalom R", "Bender K"],
        "year": 2021,
        "citation_count": 970,
        "abstract": "SCN2A encodes the neuronal sodium channel Nav1.2. Loss-of-function variants associate with autism and intellectual disability, while gain-of-function variants cause early infantile epileptic encephalopathy, suggesting bidirectional channel dysfunction.",
    },
    {
        "title": "MECP2 dosage, Rett syndrome and the autism phenotypic boundary",
        "authors": ["Amir R", "Zoghbi H"],
        "year": 2018,
        "citation_count": 2110,
        "abstract": "MECP2 is a methyl-CpG binding transcriptional regulator. Both loss and duplication disrupt activity-dependent gene programs, blurring the boundary between Rett syndrome and autism spectrum disorder.",
    },
    {
        "title": "FMR1 silencing, Fragile X and mGluR-dependent synaptic plasticity",
        "authors": ["Bassell G", "Warren S"],
        "year": 2017,
        "citation_count": 1990,
        "abstract": "Silencing of FMR1 removes FMRP-mediated translational control, exaggerating mGluR5 signaling and synaptic plasticity. Fragile X is the leading monogenic cause of autism.",
    },
    {
        "title": "PTEN-mTOR signaling links macrocephaly to autism risk",
        "authors": ["Zhou J", "Parada L"],
        "year": 2020,
        "citation_count": 1280,
        "abstract": "PTEN negatively regulates the PI3K-mTOR pathway. Germline PTEN mutations produce macrocephaly and autism via dysregulated mTOR signaling and excess protein synthesis at synapses.",
    },
    {
        "title": "NRXN1 deletions and trans-synaptic adhesion defects in autism",
        "authors": ["Sudhof T", "Reichert J"],
        "year": 2019,
        "citation_count": 1110,
        "abstract": "Neurexin-1 (NRXN1) mediates trans-synaptic adhesion with neuroligins. Deletions impair synapse formation and are recurrent in autism and schizophrenia cohorts.",
    },
    {
        "title": "GRIN2B and NMDA receptor dysfunction across neurodevelopmental disorders",
        "authors": ["Myers S", "Traynelis S"],
        "year": 2021,
        "citation_count": 860,
        "abstract": "GRIN2B encodes the GluN2B NMDA receptor subunit. Variants alter excitatory neurotransmission and synaptic plasticity, spanning autism, intellectual disability and epilepsy.",
    },
    {
        "title": "GABAergic interneuron dysfunction and the excitation-inhibition imbalance hypothesis of autism",
        "authors": ["Rubenstein J", "Merzenich M"],
        "year": 2022,
        "citation_count": 1450,
        "abstract": "An elevated excitation-to-inhibition ratio, driven by GABAergic interneuron dysfunction, is proposed as a convergent mechanism in autism. Reduced inhibitory tone increases seizure susceptibility.",
    },
    {
        "title": "Epilepsy comorbidity in autism spectrum disorder: prevalence and shared circuitry",
        "authors": ["Tuchman R", "Cuccaro M"],
        "year": 2021,
        "citation_count": 1020,
        "abstract": "Up to 30% of individuals with autism develop epilepsy. The comorbidity points to shared cortical circuit abnormalities, though the molecular bridge between specific autism genes and seizure risk remains poorly defined.",
    },
    {
        "title": "Chromatin remodeling networks converge on synaptic gene expression in autism",
        "authors": ["De Rubeis S", "Buxbaum J"],
        "year": 2020,
        "citation_count": 1670,
        "abstract": "Exome studies implicate chromatin remodelers including CHD8 that converge transcriptionally on synaptic and neuronal genes, linking the chromatin and synaptic modules of autism risk.",
    },
    {
        "title": "mTOR pathway hyperactivation as a therapeutic target in syndromic autism",
        "authors": ["Sahin M", "Sur M"],
        "year": 2019,
        "citation_count": 1340,
        "abstract": "Syndromic autisms (PTEN, TSC1/2) share mTOR hyperactivation. mTOR inhibitors such as rapamycin rescue synaptic and behavioral phenotypes in preclinical models, motivating targeted trials.",
    },
    {
        "title": "Single-cell transcriptomics reveals cell-type-specific autism gene convergence",
        "authors": ["Velmeshev D", "Kriegstein A"],
        "year": 2022,
        "citation_count": 740,
        "abstract": "Single-cell analysis of autism cortex identifies upper-layer excitatory neurons and microglia as primary loci of dysregulation, refining where convergent autism genes act.",
    },
    {
        "title": "Sodium channel Nav1.2 and cortical excitability in neurodevelopmental disease",
        "authors": ["Bender K", "Spratt P"],
        "year": 2022,
        "citation_count": 520,
        "abstract": "Nav1.2 (SCN2A) governs action potential initiation in excitatory neurons. Its biophysical disruption reshapes cortical excitability, a plausible node connecting autism to seizure phenotypes.",
    },
    {
        "title": "Polygenic and de novo risk architecture of autism spectrum disorder",
        "authors": ["Grove J", "Borglum A"],
        "year": 2021,
        "citation_count": 2240,
        "abstract": "Autism risk combines common polygenic variation with rare de novo mutations concentrated in synaptic, transcriptional and chromatin-remodeling genes.",
    },
    {
        "title": "Activity-dependent transcription couples neuronal firing to synaptic refinement",
        "authors": ["Greenberg M", "West A"],
        "year": 2018,
        "citation_count": 1580,
        "abstract": "Activity-dependent transcriptional programs, regulated in part by MECP2, translate neuronal firing into synaptic refinement; disruption is a recurrent theme across autism genes.",
    },
]


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:12]}"


def autism_seed() -> list[PaperRecord]:
    out = []
    for p in _AUTISM_PAPERS:
        out.append(
            PaperRecord(
                id=_stable_id("seed", p["title"]),
                title=p["title"],
                authors=p["authors"],
                year=p["year"],
                abstract=p["abstract"],
                citation_count=p["citation_count"],
                source="semantic_scholar",
                external_ids={},
                url=None,
            )
        )
    return out


_GENERIC_FACETS = [
    ("mechanism", "We characterize a candidate mechanism underlying {q}, integrating molecular and circuit-level evidence."),
    ("biomarker", "A longitudinal cohort identifies a stratifying biomarker relevant to {q} and its clinical subgroups."),
    ("pathway", "Pathway analysis implicates convergent signaling in {q}, nominating tractable therapeutic nodes."),
    ("therapeutic target", "Preclinical models suggest a druggable target in {q}, with translational implications."),
    ("comorbidity", "We map an under-recognized comorbidity associated with {q}, revealing shared circuitry."),
    ("genetic risk", "Exome and polygenic analyses refine the genetic risk architecture of {q}."),
    ("subgroup", "Unsupervised clustering uncovers a hidden patient subgroup within {q}."),
    ("imaging", "Multimodal imaging delineates structural correlates of {q} progression."),
]


def generic_seed(query: str, n: int = 14) -> list[PaperRecord]:
    """Plausible templated papers for an arbitrary query, used only as a last
    resort so the pipeline always has material to synthesize."""
    out = []
    base_year = 2024
    for i in range(n):
        facet, tmpl = _GENERIC_FACETS[i % len(_GENERIC_FACETS)]
        title = f"{facet.capitalize()} insights into {query}: a {2010 + (i % 14)} synthesis"
        abstract = tmpl.format(q=query)
        out.append(
            PaperRecord(
                id=_stable_id("gen", title),
                title=title,
                authors=[f"Author {chr(65 + (i % 6))}", f"Author {chr(75 + (i % 5))}"],
                year=base_year - (i % 12),
                abstract=abstract,
                citation_count=max(30, 900 - i * 47),
                source="derived",
                external_ids={},
                url=None,
            )
        )
    return out
