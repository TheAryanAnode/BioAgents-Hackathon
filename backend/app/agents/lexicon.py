"""Lightweight biomedical lexicon for deterministic entity extraction when the
LLM is unavailable. Not exhaustive — tuned to give a coherent graph for the
demo domains while still catching generic gene/pathway/disease mentions."""

from __future__ import annotations

import re

GENES = [
    "SHANK3", "CHD8", "SCN2A", "MECP2", "FMR1", "PTEN", "NRXN1", "GRIN2B",
    "TSC1", "TSC2", "KRAS", "TP53", "BRCA1", "BRCA2", "APP", "MAPT", "GLP-1",
    "Nav1.2", "FMRP", "mGluR5",
]

PATHWAYS = [
    "mTOR signaling", "mTOR pathway", "PI3K-mTOR", "synaptic plasticity",
    "chromatin remodeling", "GABAergic signaling", "GABAergic interneuron",
    "excitation-inhibition", "NMDA receptor", "glutamatergic synapse",
    "activity-dependent transcription", "trans-synaptic adhesion",
    "neuroinflammation", "protein synthesis", "cortical excitability",
]

DISEASES = [
    "autism", "autism spectrum disorder", "epilepsy", "intellectual disability",
    "Rett syndrome", "Fragile X", "schizophrenia", "Alzheimer", "epileptic encephalopathy",
    "macrocephaly", "seizure",
]

DRUGS = [
    "rapamycin", "mTOR inhibitor", "GLP-1 agonist",
]

_CANON = {
    "autism spectrum disorder": "autism",
    "mTOR pathway": "mTOR signaling",
    "PI3K-mTOR": "mTOR signaling",
    "GABAergic interneuron": "GABAergic signaling",
    "epileptic encephalopathy": "epilepsy",
    "seizure": "epilepsy",
    "Nav1.2": "SCN2A",
    "FMRP": "FMR1",
}

ENTITY_TYPE: dict[str, str] = {}
for g in GENES:
    ENTITY_TYPE[g.lower()] = "gene"
for p in PATHWAYS:
    ENTITY_TYPE[p.lower()] = "pathway"
for d in DISEASES:
    ENTITY_TYPE[d.lower()] = "disease"
for d in DRUGS:
    ENTITY_TYPE[d.lower()] = "drug"

_ALL_TERMS = sorted(GENES + PATHWAYS + DISEASES + DRUGS, key=len, reverse=True)

# Common biomedical / methodological acronyms that are NOT entities. Filtering
# these keeps the heuristic graph clean when the LLM is unavailable.
STOPWORDS = {
    "DNA", "RNA", "MRI", "PET", "EEG", "FMRI", "WGS", "WES", "GWAS", "SNP",
    "DSM", "ICD", "ADHD", "ASD", "CNV", "QTL", "PCR", "CSF", "BMI", "USA",
    "NIH", "FDA", "WHO", "SSC", "MSSNG", "NIEHS", "DDD", "OMIM", "IQ", "CI",
    "OR", "RR", "HR", "SD", "SE", "AI", "ML", "API", "PDF", "URL", "ID",
    "ABA", "TD", "EI", "GI", "CNS", "BBB", "AAV", "GFP", "WT", "KO",
}


def canon(name: str) -> str:
    return _CANON.get(name, name)


def is_lexicon_term(name: str) -> bool:
    return name.lower() in ENTITY_TYPE


def extract_entities(text: str) -> list[str]:
    found: list[str] = []
    low = text.lower()
    seen: set[str] = set()
    for term in _ALL_TERMS:
        if term.lower() in low:
            c = canon(term)
            if c not in seen:
                seen.add(c)
                found.append(c)
    # Catch generic gene-like tokens (e.g. ABCD1, FOXP1) not in the lexicon.
    # Require a digit OR mixed-case gene styling to avoid plain acronyms.
    for m in re.findall(r"\b[A-Z]{3,6}\d{1,2}\b", text):
        c = canon(m)
        if c not in seen and m not in STOPWORDS:
            seen.add(c)
            found.append(c)
    return found[:8]
