"""CRAFT text-to-SQL router for the chat agent.

When a user asks the chat a question that maps to one of the CRAFT / Spider-2.0
databases, we don't answer from literature — we ask CRAFT to write SQL against
the real records and run it. This keeps the "you don't query data, you
investigate it" story front-and-center in ordinary chat, not just the
hypothesis investigation flow.

Design goals:
- **Token-conscious**: at most one ``generate_sql`` + one ``execute_query`` per
  chat message (plus one cached ``list_data_connections`` in live mode). No
  extra Gemini calls — the single existing chat completion explains the rows.
- **Always answers**: with no MCP token the deterministic demo generators
  return plausible aggregates for every domain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agents.base import AgentContext
from app.services.craft_mcp import get_craft


@dataclass(frozen=True)
class CraftDomain:
    key: str
    label: str
    connection_default: str
    search_terms: tuple[str, ...]  # used to resolve the real slug in live mode
    keywords: tuple[str, ...]      # used to detect the domain from a question
    example: str


def _domains(settings) -> list[CraftDomain]:
    return [
        CraftDomain(
            "medical_imaging", "IDC medical imaging", settings.craft_idc_connection,
            ("idc", "imaging", "dicom"),
            ("idc", "imaging data commons", "dicom", "imaging modality", "modality",
             "imaging", "radiolog", "radiogenomic", "ct scan", "mri", "pet scan",
             "segmentation", "tumor imaging", "scan", "collection", "study instance"),
            "which imaging modalities cover lung cancer",
        ),
        CraftDomain(
            "medical_genomics", "PanCancer genomics", settings.craft_pancancer_connection,
            ("pancancer", "genomic", "tcga", "atlas"),
            ("pancancer", "pan-cancer", "pan cancer", "atlas", "mutation", "mutated",
             "oncogene", "genomic", "tcga", "co-mutation", "co-alteration",
             "tumor suppressor", "kras", "tp53", "egfr", "braf", "brca1", "brca2",
             "pik3ca", "stk11", "keap1", "cancer genom", "prevalence", "gene"),
            "how often is KRAS mutated in lung cancer",
        ),
        CraftDomain(
            "ecommerce", "Retail & marketplace", settings.craft_ecommerce_connection,
            ("thelook", "ecommerce", "commerce", "olist", "brazil"),
            ("ecommerce", "e-commerce", "marketplace", "churn", "orders", "customer",
             "retail", "product category", "shopping cart", "revenue", "sales",
             "shopper", "repeat purchase", "fulfillment", "shipping cost", "aov"),
            "which product categories drive the most revenue",
        ),
        CraftDomain(
            "crypto", "Blockchain / crypto", settings.craft_crypto_connection,
            ("crypto", "blockchain", "ethereum", "bitcoin"),
            ("crypto", "blockchain", "ethereum", "bitcoin", "on-chain", "onchain",
             "wallet", "token transfer", "defi", "smart contract", "gas fee",
             "transaction volume", "stablecoin", "erc-20", "erc20"),
            "which tokens have the most transfers",
        ),
        CraftDomain(
            "analytics", "Web / mobile analytics", settings.craft_ga4_connection,
            ("ga4", "analytics", "google analytics", "firebase"),
            ("ga4", "google analytics", "firebase", "session", "page view", "pageview",
             "web traffic", "conversion rate", "funnel", "event count", "app analytics",
             "bounce rate", "active users", "engagement"),
            "top events by session in GA4",
        ),
        CraftDomain(
            "supply_chain", "Code & dependencies", settings.craft_github_connection,
            ("github", "repos", "deps", "dependency", "package"),
            ("github", "repository", "repositories", "dependency", "dependencies",
             "package", "npm", "pypi", "vulnerability", "cve", "supply chain",
             "blast radius", "open source", "security advisory", "dependents",
             "most-depended", "most depended"),
            "which packages have the most dependents",
        ),
    ]


# Explicit database names — a single hit here is enough to route to CRAFT even
# if the word is ambiguous in isolation (e.g. "IDC", "atlas").
_STRONG_SIGNALS = {
    "medical_imaging": ("idc", "imaging data commons", "dicom"),
    "medical_genomics": ("pancancer", "pan-cancer", "pan cancer", "pancancer atlas"),
    "ecommerce": ("thelook", "olist"),
    "crypto": ("blockchain", "on-chain", "onchain"),
    "analytics": ("ga4", "firebase"),
    "supply_chain": ("deps.dev", "github_repos", "dependency graph"),
}


def _kw_matches(kw: str, text: str) -> bool:
    """Plural-tolerant, word-boundary keyword match.

    Phrases (containing a space/hyphen) match as substrings; single tokens match
    on word boundaries and tolerate simple plurals so "modality" catches
    "modalities" and "mutation" catches "mutations".
    """
    if " " in kw or "-" in kw or "." in kw:
        return kw in text
    variants = {kw}
    if kw.endswith("y"):
        variants.add(kw[:-1] + "ies")
    else:
        variants.add(kw + "s")
        variants.add(kw + "es")
    pattern = r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b"
    return re.search(pattern, text) is not None


def detect_domain(text: str, settings) -> CraftDomain | None:
    """Return the best-matching CRAFT database domain, or None for general chat.

    Strong signals (explicit DB names like "IDC" or "PanCancer") win immediately;
    otherwise the domain with the most keyword hits routes the question.
    """
    low = text.lower()
    domains = _domains(settings)

    # 1) Strong signal — explicit database reference always routes to CRAFT.
    for d in domains:
        for sig in _STRONG_SIGNALS.get(d.key, ()):  # type: ignore[attr-defined]
            if _kw_matches(sig, low):
                return d

    # 2) Otherwise, score by keyword hits.
    best: CraftDomain | None = None
    best_score = 0
    for d in domains:
        score = sum(1 for kw in d.keywords if _kw_matches(kw, low))
        if score > best_score:
            best, best_score = d, score
    return best if best_score >= 1 else None


def _domain_source(domain_key: str) -> str:
    """Map a domain to a SourceType-compatible citation source."""
    return {
        "medical_genomics": "craft_pancancer",
        "medical_imaging": "craft_idc",
    }.get(domain_key, "craft_pancancer")


async def run_craft_qa(ctx: AgentContext, question: str, domain: CraftDomain) -> dict | None:
    """Run the CRAFT text-to-SQL loop for a single chat question.

    Returns a payload with the connection, generated SQL, and returned rows, or
    None if the loop failed (chat then falls back to literature/general answer).
    """
    craft = get_craft()
    try:
        connection = await craft.resolve_connection(domain.connection_default, list(domain.search_terms))
        await ctx.audit(
            "craft_chat", "Route to CRAFT",
            detail=f"{domain.label} · {'live' if craft.live else 'demo'}",
            params={"connection": connection, "domain": domain.key, "question": question[:120]},
        )
        gen = await craft.generate_sql(question, connection, domain=domain.key)
        sql = str(gen.get("sql", "")).strip()
        await ctx.audit(
            "craft_chat", "generate_sql",
            detail=domain.label,
            params={"connection": connection, "sql": sql[:400], "live": gen.get("live")},
        )
        res = await craft.execute_query(sql, connection, context={"question": question}, domain=domain.key)
        rows = list(res.get("rows", []))[:12]
        columns = list(res.get("columns", []))
        await ctx.audit(
            "craft_chat", "execute_query",
            detail=f"{len(rows)} rows · {domain.label}",
            params={"connection": connection, "rowCount": len(rows), "live": res.get("live")},
        )
        return {
            "connection": connection,
            "domain": domain.key,
            "label": domain.label,
            "sql": sql,
            "rows": rows,
            "columns": columns,
            "live": bool(res.get("live")),
            "source": _domain_source(domain.key),
        }
    except Exception as exc:  # never let a data query break chat
        await ctx.audit(
            "craft_chat", "CRAFT query failed",
            detail=str(exc)[:140], status="error",
            params={"domain": domain.key},
        )
        return None
    finally:
        await craft.close()


def format_rows(rows: list[dict], columns: list[str], limit: int = 8) -> str:
    """Compact fixed-width table for embedding in a chat answer / LLM prompt."""
    if not rows:
        return "(query returned no rows)"
    cols = columns or list(rows[0].keys())
    header = " | ".join(cols)
    lines = [header, "-" * len(header)]
    for r in rows[:limit]:
        lines.append(" | ".join(str(r.get(c, "")) for c in cols))
    return "\n".join(lines)
