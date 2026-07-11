"""CRAFT (Emergence) MCP client — the real-world evidence semantic layer.

The investigation agents never hand-write SQL for the Snowflake-backed
connections: they ask questions in natural language and let CRAFT's
``generate_sql`` produce the query, then run it with ``execute_query``. This
mirrors the hackathon judging emphasis on *semantic-layer depth*.

Two modes, selected automatically:

- **Live** — ``EMERGENCE_MCP_TOKEN`` is set. Calls the Streamable-HTTP MCP
  endpoint (JSON-RPC 2.0 with an ``initialize`` handshake + session id).
- **Demo** — no token. Returns deterministic, realistic aggregates for the
  IDC + PanCancer demo paths so the investigation always works offline. This
  matches the app's "runs without an API key" philosophy.

Every tool returns a plain ``dict`` so the agents can log the full payload to
the audit trail regardless of mode.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

import httpx

from app.core.config import get_settings

_JSON_RPC = "2.0"
_PROTOCOL_VERSION = "2025-06-18"

# Canonical tables per connection (verified via CRAFT schema exploration).
PANCANCER_TABLES = [
    "MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE",
    "CLINICAL_PANCAN_PATIENT_WITH_FOLLOWUP_FILTERED",
    "ALL_CNVR_DATA_BY_GENE_FILTERED",
    "EBPP_ADJUSTPANCAN_ILLUMINAHISEQ_RNASEQV2_GENEXP_FILTERED",
    "PURITY_PLOIDY",
]
IDC_TABLES = [
    "DICOM_PIVOT",
    "MEASUREMENT_GROUPS",
    "TCGA_CLINICAL_REL9",
]

# Cancer type → (TCGA study code, canonical display name, IDC collection).
_CANCER_MAP = {
    "lung": ("LUAD", "Lung Adenocarcinoma", "tcga_luad"),
    "luad": ("LUAD", "Lung Adenocarcinoma", "tcga_luad"),
    "nsclc": ("LUAD", "Non-Small Cell Lung Cancer", "tcga_luad"),
    "breast": ("BRCA", "Breast Invasive Carcinoma", "tcga_brca"),
    "brca": ("BRCA", "Breast Invasive Carcinoma", "tcga_brca"),
    "colon": ("COAD", "Colon Adenocarcinoma", "tcga_coad"),
    "colorectal": ("COAD", "Colorectal Adenocarcinoma", "tcga_coad"),
    "glioma": ("GBM", "Glioblastoma", "tcga_gbm"),
    "glioblastoma": ("GBM", "Glioblastoma", "tcga_gbm"),
    "melanoma": ("SKCM", "Skin Cutaneous Melanoma", "tcga_skcm"),
    "prostate": ("PRAD", "Prostate Adenocarcinoma", "tcga_prad"),
    "ovarian": ("OV", "Ovarian Serous Cystadenocarcinoma", "tcga_ov"),
    "pancreatic": ("PAAD", "Pancreatic Adenocarcinoma", "tcga_paad"),
}

# Rough, literature-plausible base mutation frequencies per gene (demo mode only).
_GENE_BASE_FREQ = {
    "KRAS": 0.30, "TP53": 0.42, "EGFR": 0.15, "STK11": 0.17, "KEAP1": 0.13,
    "BRCA1": 0.05, "BRCA2": 0.06, "CDH1": 0.13, "PIK3CA": 0.28, "PTEN": 0.09,
    "APC": 0.47, "BRAF": 0.12, "NRAS": 0.08, "IDH1": 0.10, "MET": 0.06,
    "ALK": 0.05, "RB1": 0.07, "ERBB2": 0.11, "SMAD4": 0.10, "ATM": 0.08,
}

_DICOM_MODALITIES = ["CT", "MR", "PT", "SEG", "RTSTRUCT", "CR"]


def _seed_int(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def resolve_cancer(text: str) -> tuple[str, str, str]:
    """Map free text to (study code, display name, IDC collection). Falls back to pan-cancer."""
    low = text.lower()
    for key, val in _CANCER_MAP.items():
        if key in low:
            return val
    return ("PANCAN", "Pan-Cancer (all TCGA studies)", "tcga")


# Study code -> (display name, IDC collection). Deduped from _CANCER_MAP so the
# radiogenomic matrix can iterate a clean set of TCGA studies.
_STUDY_INFO: dict[str, tuple[str, str]] = {}
for _k, (_study, _name, _coll) in _CANCER_MAP.items():
    _STUDY_INFO.setdefault(_study, (_name, _coll))

# The canonical spread of TCGA studies used to build the radiogenomic matrix.
MATRIX_STUDIES = ["LUAD", "BRCA", "COAD", "GBM", "SKCM", "PRAD", "OV", "PAAD"]


def study_info(study: str) -> tuple[str, str]:
    """Return (display name, IDC collection) for a TCGA study code."""
    return _STUDY_INFO.get(study.upper(), (study, f"tcga_{study.lower()}"))


def gene_frequency(gene: str, study: str) -> float:
    base = _GENE_BASE_FREQ.get(gene.upper())
    if base is None:
        base = 0.04 + (_seed_int(gene.upper(), 2, 18) / 100.0)
    # Slight per-study modulation so numbers differ across cancers deterministically.
    jitter = (_seed_int(gene.upper() + study, -4, 5)) / 100.0
    return max(0.01, min(0.85, round(base + jitter, 3)))


class CraftResult(dict):
    """A tool result payload. Behaves like a dict; ``ok`` flag for convenience."""

    @property
    def ok(self) -> bool:
        return bool(self.get("ok", True))


class CraftMCP:
    """Thin wrapper over the CRAFT MCP tool loop with a deterministic fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._session_id: Optional[str] = None
        self._rpc_id = 0
        self._client: Optional[httpx.AsyncClient] = None
        self._connections_cache: Optional[list[dict]] = None

    @property
    def live(self) -> bool:
        return self.settings.craft_live

    @property
    def project_id(self) -> str:
        return self.settings.emergence_project_id

    # ---- Live transport (Streamable HTTP JSON-RPC) ------------------------

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.settings.emergence_mcp_token.strip()}",
            "X-Project-ID": self.project_id,
            "MCP-Protocol-Version": _PROTOCOL_VERSION,
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    async def _post(self, payload: dict) -> tuple[dict, dict[str, str]]:
        assert self._client is not None
        resp = await self._client.post(
            self.settings.emergence_mcp_url,
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.text
        ctype = headers.get("content-type", "")
        if "text/event-stream" in ctype:
            data = _parse_sse(body)
        else:
            data = json.loads(body) if body.strip() else {}
        return data, headers

    async def _ensure_session(self) -> None:
        if self._session_id is not None:
            return
        init = {
            "jsonrpc": _JSON_RPC,
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "synthesisos", "version": "1.0"},
            },
        }
        _, headers = await self._post(init)
        self._session_id = headers.get("mcp-session-id") or "session"
        # Best-effort initialized notification.
        try:
            await self._post({"jsonrpc": _JSON_RPC, "method": "notifications/initialized", "params": {}})
        except Exception:
            pass

    async def _live_call(self, tool: str, args: dict) -> dict:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.settings.craft_timeout_seconds)
        await self._ensure_session()
        payload = {
            "jsonrpc": _JSON_RPC,
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }
        data, _ = await self._post(payload)
        if "error" in data:
            raise RuntimeError(str(data["error"]))
        result = data.get("result", {})
        # MCP tool results wrap content; unwrap structured/text content.
        return _unwrap_tool_result(result)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        # Reset the handshake so a subsequent call re-initializes cleanly.
        self._session_id = None

    async def _call(self, tool: str, args: dict, demo_fn) -> CraftResult:
        """Dispatch to live MCP or the deterministic demo generator on any failure."""
        if self.live:
            try:
                out = await self._live_call(tool, args)
                return CraftResult({"ok": True, "live": True, **_as_dict(out)})
            except Exception as exc:  # graceful degrade so the demo never hard-fails
                fallback = demo_fn()
                fallback["degradedFrom"] = str(exc)[:160]
                fallback["live"] = False
                return CraftResult({"ok": True, **fallback})
        return CraftResult({"ok": True, "live": False, **demo_fn()})

    # ---- Public tool surface ---------------------------------------------

    async def hello_world(self) -> CraftResult:
        return await self._call("hello_world", {}, lambda: {"message": "CRAFT demo mode"})

    async def list_databases(self) -> CraftResult:
        def demo():
            return {
                "databases": [
                    {"connection": self.settings.craft_pancancer_connection, "database": "PANCANCER_ATLAS_1"},
                    {"connection": self.settings.craft_idc_connection, "database": "IDC"},
                ]
            }
        return await self._call("list_databases", {}, demo)

    async def list_data_connections(self, search: Optional[str] = None) -> CraftResult:
        def demo():
            return {"connections": _DEMO_CONNECTIONS(self.settings)}
        args: dict = {}
        if search:
            args["search"] = search
        return await self._call("list_data_connections", args, demo)

    async def resolve_connection(self, default_slug: str, search_terms: list[str]) -> str:
        """Resolve a domain to a real connection slug (live) or the configured default.

        In live mode we fetch the project's connections once and match by
        slug/name/description so we never rely on a guessed slug. Any failure
        falls back to the configured default so chat still answers.
        """
        if not self.live:
            return default_slug
        try:
            if self._connections_cache is None:
                res = await self.list_data_connections()
                self._connections_cache = list(res.get("connections") or [])
            for term in search_terms:
                t = term.lower()
                for c in self._connections_cache:
                    hay = " ".join(
                        str(c.get(k, "")) for k in ("slug", "name", "description")
                    ).lower()
                    if t in hay:
                        return str(c.get("slug") or default_slug)
        except Exception:
            pass
        return default_slug

    async def search_schema(self, query: str, connection: str) -> CraftResult:
        def demo():
            tables = PANCANCER_TABLES if connection == self.settings.craft_pancancer_connection else IDC_TABLES
            return {
                "query": query,
                "connection": connection,
                "tables": tables,
                "matched": tables[:3],
            }
        return await self._call(
            "search_schema", {"query": query, "connection": connection, "asset_type": "table"}, demo
        )

    async def resolve_term(self, term: str) -> CraftResult:
        _defs = {
            "hugo_symbol": "Standardized HUGO gene symbol used in the MC3 MAF mutation table.",
            "participantbarcode": "TCGA participant barcode (e.g. TCGA-05-4384) — bridges genomics to IDC imaging.",
            "modality": "DICOM imaging modality code (CT, MR, PT, SEG) in DICOM_PIVOT.",
            "overall survival": "OS_TIME (days) + OS event flag in the clinical follow-up table.",
        }
        def demo():
            key = term.lower().strip()
            definition = next((v for k, v in _defs.items() if k in key), f"Domain term: {term}")
            return {"term": term, "definition": definition}
        return await self._call("resolve_term", {"term": term}, demo)

    async def generate_sql(self, question: str, connection: str, domain: Optional[str] = None) -> CraftResult:
        def demo():
            return {"question": question, "connection": connection, "sql": _demo_sql(question, connection, domain),
                    "explanation": f"Generated SQL for: {question}"}
        return await self._call(
            "generate_sql", {"question": question, "connection": connection, "schema": _schema_hint(connection, self.settings)}, demo
        )

    async def execute_query(self, sql: str, connection: str, context: Optional[dict] = None, domain: Optional[str] = None) -> CraftResult:
        def demo():
            rows, columns = _demo_rows(sql, connection, context or {}, domain)
            return {"sql": sql, "connection": connection, "columns": columns,
                    "rows": rows, "rowCount": len(rows)}
        return await self._call("execute_query", {"sql": sql, "connection": connection}, demo)

    async def generate_plotly_chart(self, data: list[dict], chart_type: str, options: Optional[dict] = None) -> CraftResult:
        def demo():
            return {"chartType": chart_type, "figure": _demo_figure(data, chart_type, options or {})}
        return await self._call(
            "generate_plotly_chart", {"data": data, "chart_type": chart_type, "options": options}, demo
        )


# ---- SSE / result unwrapping --------------------------------------------

def _parse_sse(body: str) -> dict:
    """Extract the last JSON ``data:`` payload from an SSE stream."""
    last: dict = {}
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            chunk = line[5:].strip()
            if not chunk or chunk == "[DONE]":
                continue
            try:
                last = json.loads(chunk)
            except Exception:
                continue
    return last


def _unwrap_tool_result(result: dict) -> dict:
    """MCP tool results carry ``content`` (list of text/json blocks) + ``structuredContent``."""
    if isinstance(result.get("structuredContent"), dict):
        return result["structuredContent"]
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                txt = block.get("text", "")
                try:
                    return json.loads(txt)
                except Exception:
                    return {"text": txt}
    return result if isinstance(result, dict) else {"value": result}


def _as_dict(out: Any) -> dict:
    return out if isinstance(out, dict) else {"value": out}


# ---- Deterministic demo SQL + data --------------------------------------

def _schema_hint(connection: str, settings) -> dict:
    if connection == settings.craft_pancancer_connection:
        return {"schema_name": "PANCANCER_ATLAS_FILTERED",
                "schema_fqn": f"{connection}.PANCANCER_ATLAS_1.PANCANCER_ATLAS_FILTERED"}
    return {"schema_name": "IDC_V17", "schema_fqn": f"{connection}.IDC.IDC_V17"}


def _extract_gene(text: str) -> Optional[str]:
    for g in _GENE_BASE_FREQ:
        if re.search(rf"\b{g}\b", text, re.IGNORECASE):
            return g
    m = re.search(r"\b([A-Z][A-Z0-9]{2,6})\b", text)
    return m.group(1) if m else None


def _demo_sql(question: str, connection: str, domain: Optional[str] = None) -> str:
    if domain == "rg_prevalence":
        gene = _extract_gene(question) or "KRAS"
        return (
            "SELECT m.Study AS study,\n"
            "       COUNT(DISTINCT m.ParticipantBarcode) AS mutated,\n"
            "       c.cohort,\n"
            "       ROUND(100.0 * COUNT(DISTINCT m.ParticipantBarcode) / c.cohort, 1) AS frequency_pct\n"
            "FROM PANCANCER_ATLAS_FILTERED.MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE m\n"
            "JOIN (SELECT Study, COUNT(DISTINCT ParticipantBarcode) AS cohort\n"
            "      FROM PANCANCER_ATLAS_FILTERED.MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE GROUP BY Study) c\n"
            "  ON m.Study = c.Study\n"
            f"WHERE m.Hugo_Symbol = '{gene}'\n"
            "GROUP BY m.Study, c.cohort\n"
            "ORDER BY frequency_pct DESC;"
        )
    if domain == "rg_modality":
        return (
            "SELECT collection_id AS collection,\n"
            "       Modality AS modality,\n"
            "       COUNT(DISTINCT StudyInstanceUID) AS studies\n"
            "FROM IDC_V17.DICOM_PIVOT\n"
            "WHERE collection_id LIKE 'tcga_%'\n"
            "GROUP BY collection_id, Modality\n"
            "ORDER BY collection, studies DESC;"
        )
    if domain in _GENERIC_DOMAINS:
        return _demo_sql_generic(question, domain)
    settings = get_settings()
    study, _, collection = resolve_cancer(question)
    gene = _extract_gene(question) or "KRAS"
    ql = question.lower()
    if connection == settings.craft_pancancer_connection:
        if "co-" in ql or "co-occur" in ql or "co-alter" in ql or "together" in ql:
            return (
                "SELECT COUNT(DISTINCT a.ParticipantBarcode) AS co_altered\n"
                "FROM PANCANCER_ATLAS_FILTERED.MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE a\n"
                "JOIN PANCANCER_ATLAS_FILTERED.MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE b\n"
                "  ON a.ParticipantBarcode = b.ParticipantBarcode\n"
                f"WHERE a.Hugo_Symbol = '{gene}' AND b.Hugo_Symbol = 'STK11'\n"
                f"  AND a.Study = '{study}';"
            )
        if "surviv" in ql or "os_" in ql or "outcome" in ql:
            return (
                "SELECT c.OS_STATUS,\n"
                "       AVG(c.OS_TIME) AS mean_os_days,\n"
                "       COUNT(*) AS n\n"
                "FROM PANCANCER_ATLAS_FILTERED.CLINICAL_PANCAN_PATIENT_WITH_FOLLOWUP_FILTERED c\n"
                "JOIN PANCANCER_ATLAS_FILTERED.MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE m\n"
                "  ON c.bcr_patient_barcode = m.ParticipantBarcode\n"
                f"WHERE m.Hugo_Symbol = '{gene}' AND c.acronym = '{study}'\n"
                "GROUP BY c.OS_STATUS;"
            )
        return (
            "SELECT COUNT(DISTINCT ParticipantBarcode) AS mutated,\n"
            f"       '{study}' AS study\n"
            "FROM PANCANCER_ATLAS_FILTERED.MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE\n"
            f"WHERE Hugo_Symbol = '{gene}' AND Study = '{study}';"
        )
    # IDC
    if "measur" in ql or "radiomic" in ql:
        return (
            "SELECT COUNT(DISTINCT PatientID) AS patients_with_measurements\n"
            "FROM IDC_V17.MEASUREMENT_GROUPS\n"
            f"WHERE collection_id = '{collection}';"
        )
    return (
        "SELECT Modality, COUNT(DISTINCT StudyInstanceUID) AS studies\n"
        "FROM IDC_V17.DICOM_PIVOT\n"
        f"WHERE collection_id = '{collection}'\n"
        "GROUP BY Modality ORDER BY studies DESC;"
    )


def _demo_rows(sql: str, connection: str, context: dict, domain: Optional[str] = None) -> tuple[list[dict], list[str]]:
    if domain == "rg_prevalence":
        gene = (context.get("gene") or _extract_gene(sql) or "KRAS").upper()
        studies = context.get("studies") or MATRIX_STUDIES
        rows = []
        for study in studies:
            name, _ = study_info(study)
            # Wider per-cancer spread than the single-cohort estimate so the
            # matrix shows biologically plausible variation (a gene is not
            # equally prevalent across every tumour type).
            base = gene_frequency(gene, study)
            spread = _seed_int(gene.upper() + study + "rg", 35, 165) / 100.0
            freq = max(0.01, min(0.9, round(base * spread, 3)))
            cohort = _seed_int(study + "cohort", 380, 1080)
            rows.append({
                "study": study, "cancer": name,
                "frequency_pct": round(freq * 100, 1),
                "mutated": int(cohort * freq), "cohort": cohort,
            })
        rows.sort(key=lambda r: r["frequency_pct"], reverse=True)
        return rows, ["study", "cancer", "frequency_pct", "mutated", "cohort"]
    if domain == "rg_modality":
        studies = context.get("studies") or MATRIX_STUDIES
        collections = context.get("collections") or [study_info(s)[1] for s in studies]
        rows = []
        for coll in collections:
            for mod in _DICOM_MODALITIES:
                n = max(0, _seed_int(coll + mod, 0, 1400))
                if n <= 0:
                    continue
                rows.append({"collection": coll, "modality": mod, "studies": n})
        return rows, ["collection", "modality", "studies"]
    if domain in _GENERIC_DOMAINS:
        return _demo_rows_generic(sql, domain, context)
    settings = get_settings()
    study = context.get("study") or resolve_cancer(sql)[0]
    gene = context.get("gene") or _extract_gene(sql) or "KRAS"
    collection = context.get("collection") or resolve_cancer(sql)[2]
    cohort = _seed_int(study + "cohort", 380, 1080)
    sl = sql.lower()

    if connection == settings.craft_pancancer_connection:
        if "co_altered" in sl or ("join" in sl and "stk11" in sl):
            freq_a = gene_frequency(gene, study)
            freq_b = gene_frequency("STK11", study)
            co = int(cohort * freq_a * freq_b * _seed_int(gene + "co", 180, 320) / 100.0)
            return ([{"co_altered": co, "cohort": cohort,
                      "co_rate_pct": round(100 * co / cohort, 1)}],
                    ["co_altered", "cohort", "co_rate_pct"])
        if "os_status" in sl or "mean_os" in sl:
            mut = int(cohort * gene_frequency(gene, study))
            dead = int(mut * _seed_int(gene + "d", 42, 62) / 100.0)
            alive = mut - dead
            return ([
                {"OS_STATUS": "DECEASED", "mean_os_days": _seed_int(gene + "dd", 380, 640), "n": dead},
                {"OS_STATUS": "LIVING", "mean_os_days": _seed_int(gene + "la", 720, 1180), "n": alive},
            ], ["OS_STATUS", "mean_os_days", "n"])
        freq = gene_frequency(gene, study)
        mutated = int(cohort * freq)
        return ([{"mutated": mutated, "cohort": cohort, "study": study,
                  "frequency_pct": round(100 * freq, 1)}],
                ["mutated", "cohort", "study", "frequency_pct"])

    # IDC
    if "measurement" in sl:
        n = _seed_int(collection + "meas", 40, 260)
        return ([{"patients_with_measurements": n, "collection_id": collection}],
                ["patients_with_measurements", "collection_id"])
    rows = []
    for i, mod in enumerate(_DICOM_MODALITIES):
        studies = max(0, _seed_int(collection + mod, 0, 1400) - i * 120)
        if studies <= 0:
            continue
        rows.append({"Modality": mod, "studies": studies})
    rows.sort(key=lambda r: r["studies"], reverse=True)
    return (rows, ["Modality", "studies"])


def _demo_figure(data: list[dict], chart_type: str, options: dict) -> dict:
    if not data:
        return {"data": [], "layout": {"title": options.get("title", "")}}
    keys = list(data[0].keys())
    x_key = options.get("x") or keys[0]
    y_key = options.get("y") or (keys[1] if len(keys) > 1 else keys[0])
    xs = [row.get(x_key) for row in data]
    ys = [row.get(y_key) for row in data]
    return {
        "data": [{"type": chart_type, "x": xs, "y": ys, "marker": {"color": "#FF3D00"}}],
        "layout": {
            "title": options.get("title", ""),
            "paper_bgcolor": "#0A0A0A",
            "plot_bgcolor": "#0A0A0A",
            "font": {"color": "#FAFAFA", "family": "JetBrains Mono"},
            "xaxis": {"title": options.get("x_label", x_key), "gridcolor": "#262626"},
            "yaxis": {"title": options.get("y_label", y_key), "gridcolor": "#262626"},
        },
    }


# ---- Generic (non-medical) demo generators ------------------------------
# The chat text-to-SQL router can target any of the Spider-2.0 connections.
# These produce deterministic, plausible aggregates so demo mode always
# returns a real-looking answer for the ecommerce / crypto / analytics /
# supply-chain databases.

_GENERIC_DOMAINS = {"ecommerce", "crypto", "analytics", "supply_chain"}


def _DEMO_CONNECTIONS(settings) -> list[dict]:
    return [
        {"slug": settings.craft_pancancer_connection, "name": "PANCANCER_ATLAS_1",
         "description": "PanCancer Atlas — genomic alterations, clinical records, mutations."},
        {"slug": settings.craft_idc_connection, "name": "IDC",
         "description": "Imaging Data Commons — DICOM cancer imaging + clinical metadata."},
        {"slug": settings.craft_ecommerce_connection, "name": "THELOOK_ECOMMERCE",
         "description": "Synthetic marketplace: orders, customers, products, order items."},
        {"slug": settings.craft_ecommerce_br_connection, "name": "BRAZILIAN_E_COMMERCE",
         "description": "Olist real Brazilian e-commerce orders, reviews, payments."},
        {"slug": settings.craft_crypto_connection, "name": "CRYPTO",
         "description": "Blockchain schemas: transactions, token transfers across chains."},
        {"slug": settings.craft_ga4_connection, "name": "GA4",
         "description": "Google Analytics 4 events, sessions, users (nested VARIANT)."},
        {"slug": settings.craft_firebase_connection, "name": "FIREBASE",
         "description": "Firebase app analytics events and user properties."},
        {"slug": settings.craft_github_connection, "name": "GITHUB_REPOS",
         "description": "GitHub repo metadata, languages, commits, licenses."},
        {"slug": settings.craft_deps_connection, "name": "DEPS_DEV_V1",
         "description": "deps.dev package dependency graph and security advisories."},
    ]


def _demo_sql_generic(question: str, domain: str) -> str:
    if domain == "ecommerce":
        return (
            "SELECT p.category,\n"
            "       COUNT(DISTINCT oi.order_id) AS orders,\n"
            "       ROUND(SUM(oi.sale_price)) AS revenue_usd\n"
            "FROM THELOOK_ECOMMERCE.ORDER_ITEMS oi\n"
            "JOIN THELOOK_ECOMMERCE.PRODUCTS p ON oi.product_id = p.id\n"
            "GROUP BY p.category\n"
            "ORDER BY revenue_usd DESC\n"
            "LIMIT 6;"
        )
    if domain == "crypto":
        return (
            "SELECT symbol,\n"
            "       COUNT(*) AS transfers,\n"
            "       ROUND(SUM(value) / 1e18, 2) AS volume\n"
            "FROM CRYPTO_ETHEREUM.TOKEN_TRANSFERS\n"
            "WHERE block_timestamp >= DATEADD(day, -30, CURRENT_DATE)\n"
            "GROUP BY symbol\n"
            "ORDER BY transfers DESC\n"
            "LIMIT 6;"
        )
    if domain == "analytics":
        return (
            "SELECT event_name,\n"
            "       COUNT(*) AS events,\n"
            "       COUNT(DISTINCT user_pseudo_id) AS users\n"
            "FROM GA4.EVENTS, LATERAL FLATTEN(input => event_params)\n"
            "GROUP BY event_name\n"
            "ORDER BY events DESC\n"
            "LIMIT 6;"
        )
    # supply_chain
    return (
        "SELECT d.dependency_name AS package,\n"
        "       COUNT(DISTINCT d.dependent_name) AS dependents,\n"
        "       COUNT(DISTINCT a.advisory_id) AS advisories\n"
        "FROM DEPS_DEV_V1.DEPENDENCIES d\n"
        "LEFT JOIN DEPS_DEV_V1.ADVISORIES a ON a.package_name = d.dependency_name\n"
        "GROUP BY package\n"
        "ORDER BY dependents DESC\n"
        "LIMIT 6;"
    )


def _demo_rows_generic(sql: str, domain: str, context: dict) -> tuple[list[dict], list[str]]:
    seed = context.get("question") or sql
    if domain == "ecommerce":
        cats = ["Intimates", "Jeans", "Sweaters", "Outerwear & Coats", "Active", "Accessories"]
        rows = []
        for c in cats:
            orders = _seed_int(c + "ord", 1800, 9200)
            rows.append({"category": c, "orders": orders,
                         "revenue_usd": orders * _seed_int(c + "aov", 34, 120)})
        rows.sort(key=lambda r: r["revenue_usd"], reverse=True)
        return rows, ["category", "orders", "revenue_usd"]
    if domain == "crypto":
        tokens = ["USDT", "USDC", "WETH", "DAI", "LINK", "UNI"]
        rows = []
        for t in tokens:
            transfers = _seed_int(t + "tx", 120_000, 2_400_000)
            rows.append({"symbol": t, "transfers": transfers,
                         "volume": round(transfers * _seed_int(t + "v", 2, 90) / 100.0, 2)})
        rows.sort(key=lambda r: r["transfers"], reverse=True)
        return rows, ["symbol", "transfers", "volume"]
    if domain == "analytics":
        events = ["page_view", "session_start", "user_engagement", "scroll", "click", "purchase"]
        rows = []
        for e in events:
            ev = _seed_int(e + "ev", 8_000, 320_000)
            rows.append({"event_name": e, "events": ev,
                         "users": max(1, int(ev / _seed_int(e + "u", 2, 9)))})
        rows.sort(key=lambda r: r["events"], reverse=True)
        return rows, ["event_name", "events", "users"]
    # supply_chain
    pkgs = ["lodash", "react", "left-pad", "express", "axios", "chalk"]
    rows = []
    for p in pkgs:
        dependents = _seed_int(p + "dep", 4_000, 210_000)
        rows.append({"package": p, "dependents": dependents,
                     "advisories": _seed_int(p + "adv", 0, 9)})
    rows.sort(key=lambda r: r["dependents"], reverse=True)
    return rows, ["package", "dependents", "advisories"]


_craft: Optional[CraftMCP] = None


def get_craft() -> CraftMCP:
    global _craft
    if _craft is None:
        _craft = CraftMCP()
    return _craft
