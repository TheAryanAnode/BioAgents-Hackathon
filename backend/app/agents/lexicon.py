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
# Word-boundary matchers so short gene symbols (e.g. "APP", "MET") don't match
# inside ordinary words ("application", "method"). Multiword terms match as a
# whole phrase.
_TERM_RE = {t: re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in _ALL_TERMS}

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


# ---- Domain-agnostic extraction -----------------------------------------
# The curated lexicon above only covers the neuro/autism demo. To make the
# pipeline reliable for ANY topic (asthma, lung cancer, crypto, etc.) we add a
# lightweight statistical keyphrase extractor: capitalized noun phrases,
# biomedical-suffix words, and gene-like tokens. It needs no LLM and no network,
# and the analysis stage keeps only phrases that recur across ≥2 papers so noise
# is filtered by document frequency.

# Morphological suffixes that mark a token as a biomedical concept even when it
# is not capitalized (e.g. "asthma", "carcinoma", "inflammation").
_BIO_SUFFIX = (
    "cancer", "carcinoma", "sarcoma", "lymphoma", "melanoma", "glioma", "tumour",
    "tumor", "itis", "osis", "aemia", "emia", "pathy", "penia", "plasia",
    "trophy", "fibrosis", "sclerosis", "syndrome", "disease", "disorder",
    "deficiency", "infection", "inflammation", "asthma", "diabetes",
    "signaling", "signalling", "pathway", "receptor", "kinase", "cytokine",
    "antibody", "antigen", "enzyme", "hormone", "peptide", "metabolism",
    "apoptosis", "angiogenesis", "immunity", "microbiome",
)

_DRUG_SUFFIX = ("mab", "nib", "tinib", "inib", "stat", "prazole", "cycline",
                "mycin", "sartan", "pril", "vir", "azole", "parin")

_PATHWAY_HINT = ("signaling", "signalling", "pathway", "receptor", "kinase",
                 "cascade", "axis", "checkpoint", "transduction")

_DISEASE_HINT = ("cancer", "carcinoma", "sarcoma", "lymphoma", "melanoma",
                 "glioma", "tumour", "tumor", "itis", "osis", "emia", "pathy",
                 "fibrosis", "sclerosis", "syndrome", "disease", "disorder",
                 "deficiency", "infection", "inflammation", "asthma", "diabetes",
                 "obesity", "hypertension", "stroke", "seizure")

# Very common words that must not become standalone concepts.
_GENERIC_STOP = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "with", "to", "from",
    "by", "we", "our", "this", "that", "these", "those", "study", "studies",
    "results", "using", "used", "use", "show", "shows", "showed", "novel", "new",
    "here", "between", "among", "via", "role", "effect", "effects", "analysis",
    "patients", "patient", "clinical", "significant", "associated", "association",
    "may", "can", "could", "also", "however", "therefore", "thus", "both",
    "within", "data", "model", "models", "approach", "method", "methods", "paper",
    "review", "background", "objective", "conclusion", "conclusions", "findings",
    "finding", "compared", "increase", "increased", "decrease", "decreased",
    "high", "low", "level", "levels", "human", "mouse", "mice", "vivo", "vitro",
    "report", "reports", "suggest", "suggests", "identify", "identified", "we",
    "based", "including", "recent", "present", "current", "potential", "important",
    "different", "various", "large", "small", "higher", "lower", "risk", "type",
    "group", "groups", "case", "cases", "control", "controls", "years", "year",
    "age", "male", "female", "total", "mean", "rate", "rates", "number", "one",
    "two", "three", "first", "second", "cohort", "trial", "outcome", "outcomes",
}

_GENE_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,6}\d?\b")
# Capitalized phrases (1–3 words) — proper-noun-like named entities.
_PHRASE_RE = re.compile(r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+){0,2})\b")
_WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z-]{3,}\b")


def guess_type(term: str) -> str:
    """Classify a term into gene/pathway/disease/drug/concept using morphology."""
    low = term.lower()
    if low in ENTITY_TYPE:
        return ENTITY_TYPE[low]
    words = low.split()
    if any(w.endswith(_DRUG_SUFFIX) for w in words) or "inhibitor" in low or "agonist" in low:
        return "drug"
    if any(h in low for h in _PATHWAY_HINT):
        return "pathway"
    if any(w.endswith(tuple(s for s in _DISEASE_HINT)) or w in _DISEASE_HINT for w in words) \
            or any(h in low for h in _DISEASE_HINT):
        return "disease"
    # Gene-like: short all-caps token, optionally with a digit (KRAS, EGFR, IL13).
    if re.fullmatch(r"[A-Z][A-Z0-9]{1,6}\d?", term):
        return "gene"
    return "concept"


def _norm_display(term: str) -> str:
    """Deterministic display form so the same concept groups across papers."""
    term = re.sub(r"\s+", " ", term).strip(" -")
    # Preserve gene/acronym tokens as-is (all upper, e.g. EGFR, IL13, TP53).
    if re.fullmatch(r"[A-Z][A-Z0-9]{1,6}\d?", term):
        return term
    # Title-case multiword / lowercase phrases ("lung cancer" -> "Lung Cancer").
    return " ".join(w if w.isupper() else w.capitalize() for w in term.split())


_STOP_LC = {s.lower() for s in STOPWORDS}
# Connective / verb-ish tokens that should never sit inside a concept phrase.
_CONNECTIVE = _GENERIC_STOP | {
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "drive",
    "drives", "driven", "links", "link", "linked", "causes", "cause", "caused",
    "leads", "lead", "induces", "induce", "regulates", "regulate", "promotes",
    "promote", "inhibits", "inhibit", "affects", "affect", "reveals", "reveal",
    "contributes", "contribute", "as", "at", "into", "through", "during", "over",
    "under", "not", "but", "than", "then", "when", "while", "such", "more",
    "most", "less", "least", "its", "their", "which", "who", "whose",
}


def _clean_phrase(phrase: str) -> str | None:
    """Trim connectives and return the longest contiguous run of content words."""
    words = phrase.split()
    best: list[str] = []
    run: list[str] = []
    for w in words:
        if w.lower() in _CONNECTIVE:
            if len(run) > len(best):
                best = run
            run = []
        else:
            run.append(w)
    if len(run) > len(best):
        best = run
    if not best:
        return None
    return " ".join(best)


# Bare category words that are too generic to be a concept on their own
# (but fine inside a phrase, e.g. "Lung Cancer", "mTOR Pathway").
_TOO_GENERIC = {
    "disease", "diseases", "disorder", "disorders", "pathway", "pathways",
    "cancer", "cancers", "tumor", "tumors", "tumour", "tumours", "syndrome",
    "syndromes", "infection", "infections", "receptor", "receptors", "kinase",
    "kinases", "cytokine", "cytokines", "protein", "proteins", "gene", "genes",
    "mutation", "mutations", "expression", "therapy", "therapies", "cell",
    "cells", "signaling", "signalling", "enzyme", "enzymes", "hormone",
    "hormones", "peptide", "peptides", "antibody", "antibodies", "antigen",
    "antigens", "carcinoma", "sarcoma",
}


def _is_meaningful(term: str) -> bool:
    low = term.lower()
    if low in _GENERIC_STOP or low in _STOP_LC:
        return False
    words = low.split()
    if all(w in _GENERIC_STOP for w in words):
        return False
    # Single bare category word is not a useful concept endpoint.
    if len(words) == 1 and low in _TOO_GENERIC:
        return False
    return True


def extract_keyphrases(text: str, limit: int = 12) -> list[str]:
    """Domain-agnostic candidate concepts from a title+abstract (no LLM)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        disp = _norm_display(raw)
        key = disp.lower()
        if len(key) < 3 or key in seen or not _is_meaningful(disp):
            return
        seen.add(key)
        out.append(disp)

    # 1) Gene-like tokens (KRAS, EGFR, IL13, TP53) — high precision.
    for m in _GENE_RE.findall(text):
        if m not in STOPWORDS and not m.isdigit():
            add(m)
    # 2) Capitalized multiword phrases (named entities like "Lung Cancer").
    for m in _PHRASE_RE.findall(text):
        cleaned = _clean_phrase(m)
        if cleaned and len(cleaned.split()) >= 2:
            add(cleaned)
    # 3) Single biomedical-suffix words anywhere (asthma, inflammation).
    for m in _WORD_RE.findall(text):
        if m.lower().endswith(_BIO_SUFFIX):
            add(m)
    return out[:limit]


def extract_entities(text: str) -> list[str]:
    """Lexicon hits first (curated demo domains), then generic keyphrases so the
    graph is populated for ANY research topic."""
    found: list[str] = []
    seen: set[str] = set()
    for term in _ALL_TERMS:
        if _TERM_RE[term].search(text):
            c = canon(term)
            if c.lower() not in seen:
                seen.add(c.lower())
                found.append(c)
    for kp in extract_keyphrases(text):
        c = canon(kp)
        if c.lower() not in seen:
            seen.add(c.lower())
            found.append(c)
    return found[:10]
