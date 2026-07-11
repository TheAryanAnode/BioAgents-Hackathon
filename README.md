# SynthesisOS — You Don't Query Data. You Investigate It.

> **Enterprise Agents Hackathon** · Emergence AI CRAFT + Nebius Token Factory  
> Autonomous literature synthesis meets real-world evidence investigation — form a hypothesis from the literature, interrogate enterprise-scale patient data through CRAFT's semantic layer, and deliver an insight someone would actually act on.

SynthesisOS is a full-stack agentic research platform. Give it a biomedical question and a team of agents ingests scientific literature (Semantic Scholar, PubMed, arXiv, and your own PDFs), builds an interactive knowledge graph, generates novel hypotheses from structural gaps, and — when you select a hypothesis — **investigates it against real TCGA genomics and DICOM imaging records** via Emergence AI's CRAFT MCP. Every tool call, SQL generation, and model invocation streams to a live audit trail so anyone can follow what the agent did and why.

Built for the **Biotech / clinical** challenge: test whether imaging modalities correlate with molecular subtypes across cancers — publication-quality radiogenomic analysis with no genomics expertise required, because CRAFT resolves the terminology for you.

---

## The before/after moment

Paste a nested GA4 schema into a generic assistant and ask for *"top pages by engagement time"* → broken SQL. Ask CRAFT → correct `LATERAL FLATTEN`. SynthesisOS takes that further: your agent doesn't hand-write queries. It forms a hypothesis from literature, asks CRAFT questions in plain English, and stitches genomic prevalence, imaging modality coverage, and survival stratification into a tri-modal validation scorecard an analyst would actually use.

---

## What makes it different

### Investigation, not queries
The product story is a closed loop: **literature → hypothesis → CRAFT interrogation → actionable finding**. Selecting a hypothesis (H01, H02, …) automatically triggers an 18-step CRAFT investigation. Chat does the same on demand — ask about KRAS mutation rates or e-commerce churn and the agent routes to the right Spider 2.0 database, runs `generate_sql` → `execute_query`, and explains the rows.

### Semantic layer depth
Agents never write raw SQL against Snowflake. Every data touchpoint goes through CRAFT's MCP tool loop:

| Tool | Role in SynthesisOS |
|------|---------------------|
| `list_data_connections` | Resolve the live connection slug for any Spider 2.0 database |
| `search_schema` | Planner discovers relevant tables before asking questions |
| `resolve_term` | Map biomedical jargon (HUGO symbols, TCGA barcodes, DICOM modalities) to schema |
| `generate_sql` | Natural-language questions → accurate SQL (including `LATERAL FLATTEN` patterns) |
| `execute_query` | Run against real enterprise records; results feed evidence + scorecard |
| `generate_plotly_chart` | Modality-coverage charts in the investigation synthesizer |

Investigation agents and chat share one `CraftMCP` client with graceful demo-mode fallback — the feature always works, with or without an API token.

### Actionable findings
Literature alone gives you a hypothesis. CRAFT gives you numbers:

- **Tri-modal validation scorecard** — Literature vs. genomics vs. imaging alignment, with a revised confidence score
- **Commercial grounding** — Patient population, unmet need, and ROI recomputed from CRAFT-measured mutation frequencies and cancer incidence
- **Radiogenomic synthesis** — Does imaging modality coverage track molecular class? The synthesizer agent answers with data, not speculation
- **CRAFT dataset nodes** — Investigation results populate the knowledge graph with linked `dataset` nodes (PanCancer + IDC) so evidence is visible, not buried in logs

### Multi-agent architecture
Two LangGraph orchestrators, specialized delegation, and error recovery at every layer:

```
Literature pipeline (automatic)
  Ingestion → Analysis → Graph → Hypothesis → Evidence → Commercial

CRAFT investigation sub-graph (user-initiated, per hypothesis)
  Planner → PanCancer Analyst → Imaging Analyst → Radiogenomics Synthesizer
```

| Agent | Responsibility |
|-------|----------------|
| **Ingestion** | Fetch papers (Semantic Scholar / PubMed / arXiv) + ingest user PDFs; chunk and embed |
| **Analysis** | Extract biomedical entities and relations (domain lexicon — no LLM in pipeline) |
| **Graph Builder** | NetworkX graph, centrality, clusters; exports concepts, papers, and CRAFT datasets |
| **Hypothesis** | Detect open triangles in the graph; generate testable mechanisms |
| **Evidence** | Retrieve chunks, classify stance (support / contradict), score confidence over time |
| **Commercial** | Patient subgroups, unmet need, whitespace, ROI — grounded in CRAFT epidemiology after investigation |
| **Planner** | Scope investigation, resolve domain terms, identify PanCancer + IDC tables |
| **PanCancer Analyst** | Mutation prevalence, co-alteration, survival stratification via CRAFT |
| **Imaging Analyst** | DICOM modality distribution, quantitative measurement availability |
| **Radiogenomics Synthesizer** | Tri-modal scorecard, revised confidence, Plotly chart, narrative finding |
| **CRAFT Chat Router** | Detects which Spider 2.0 database a question maps to; runs text-to-SQL in chat |

### Transparent reasoning
Every step is explainable in the UI and exportable for compliance:

- **Investigation Timeline** — 18 steps with phase legend (plan → genomics → imaging → synthesis), NL question, CRAFT tool, generated SQL, row preview, and *why / what's next*
- **Scientific Whiteboard** — Auto-generated pathway, interaction, progression, and cascade diagrams from gap entities (no extra AI calls)
- **Audit log** — Live WebSocket stream with CRAFT filter; expanded entries show SQL snippets
- **Confidence explainer** — How literature evidence, CRAFT data, and stance weighting combine

---

## CRAFT databases

SynthesisOS connects to all nine Spider 2.0 benchmark databases through CRAFT MCP. The chat router auto-detects the domain; the investigation flow targets the biotech pair.

| Domain | Databases | Example question |
|--------|-----------|------------------|
| **Biotech / clinical** | IDC (4.8M rows) + PANCANCER_ATLAS_1 (18.9M rows) | *"How often is KRAS mutated in lung adenocarcinoma, and which imaging modalities cover that cohort?"* |
| E-commerce | THELOOK_ECOMMERCE + BRAZILIAN_E_COMMERCE | *"Which product categories drive the most revenue?"* |
| Crypto / blockchain | CRYPTO (158M rows, 7 schemas) | *"Which tokens have the most cross-chain transfers?"* |
| Digital analytics | GA4 + FIREBASE | *"Top events by session — nested VARIANT/ARRAY schemas"* |
| Dev infrastructure | GITHUB_REPOS + DEPS_DEV_V1 | *"Which packages have the largest dependency blast radius?"* |

**IDC** — DICOM imaging metadata, clinical context, derived measurements (`DICOM_PIVOT`, `MEASUREMENT_GROUPS`, `TCGA_CLINICAL_REL9`).  
**PanCancer Atlas** — Harmonized mutations, CNVR, expression, and clinical follow-up across 33 TCGA cancer types.  
**TCGA barcodes** bridge genomics to imaging for radiogenomic investigation.

---

## Architecture

```
React + Vite (Bold Typography UI)
   │  REST + WebSocket  (Vite proxy → :8000)
   ▼
FastAPI  ──►  LangGraph orchestrator
   │              │  literature pipeline (ingestion → … → commercial)
   │              │  investigation sub-graph (planner → … → synthesizer)
   │              │  CRAFT chat router (domain detect → text-to-SQL)
   ▼
   Semantic Scholar · PubMed · arXiv · user PDFs · Nebius Token Factory (MiniMax-M3)
   Emergence CRAFT MCP (IDC + PanCancer + 7 other Spider 2.0 connections)
   ▼
   ChromaDB (vectors) · SQLite (provenance/audit) · NetworkX (graph compute)
```

**Modes:** Home (research query) · Auto (deterministic hot-topic launcher, zero API cost) · Graph · Hypotheses · Chat — persistent navbar on every view.

**Inference:** Nebius Token Factory (`MiniMaxAI/MiniMax-M3`) via OpenAI-compatible chat completions for chat, hypothesis enrichment, reports, and synthesizer narrative (user-initiated only). The literature pipeline and Auto mode use fast heuristics so credits are never burned on background work.

---

## Quick start

### One command (backend + frontend)

From the repo root:

```bash
chmod +x run.sh   # first time only
./run.sh
```

Open http://localhost:5173. **Ctrl+C** stops both servers. Optional: `BACKEND_PORT=8001 FRONTEND_PORT=5174 ./run.sh`

On first run, `run.sh` creates the Python venv, installs dependencies if needed, and copies `backend/.env.example` → `backend/.env`.

### Manual start

#### 1. Backend (Python 3.12)

```bash
cd backend
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

The server prints its mode on startup, e.g. `nebius=on model=MiniMaxAI/MiniMax-M3 craft=demo embeddings=hashing`.

#### 2. Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` and `/ws` to the backend on `:8000`.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `NEBIUS_API_KEY` | Nebius Token Factory for chat, hypothesis click, reports (optional — demo mode works without) |
| `NEBIUS_BASE_URL` | OpenAI-compatible endpoint (default: `https://api.tokenfactory.us-central1.nebius.com/v1`) |
| `NEBIUS_MODEL` | Inference model (default: `MiniMaxAI/MiniMax-M3`) |
| `EMERGENCE_MCP_TOKEN` | Live CRAFT MCP access (optional — deterministic demo aggregates without) |
| `EMERGENCE_PROJECT_ID` | Emergence project UUID |
| `CRAFT_PANCANCER_CONNECTION` / `CRAFT_IDC_CONNECTION` | Default connection slugs (auto-resolved live via `list_data_connections`) |
| `CRAFT_MAX_QUERIES_PER_INVESTIGATION` | Cap per investigation (default 6) |

> **Token mindfulness:** The research pipeline never calls the LLM. Nebius is used only for user-initiated chat, hypothesis enrichment, and reports. CRAFT investigation and chat text-to-SQL are capped per message. Auto mode is fully offline.

---

## Demo flow (≈5 minutes)

1. **Query** — Enter `KRAS G12C lung cancer resistance` on Home, or pick a hot topic from **Auto** (no API cost).
2. **Live ingestion** — Open the Audit toggle. Watch agents fetch from Semantic Scholar, PubMed, and arXiv as paper nodes animate into the graph.
3. **Explore the graph** — Concepts (vermillion), papers (white), uploads (green), CRAFT datasets (accent glow). Click a gene node; filter by year or source.
4. **Hypotheses** — Switch to Hypotheses. Click **H01** — Nebius enriches the card (if live) and **CRAFT investigation starts automatically**.
5. **Investigation Timeline** — Watch 18 steps stream: planner scopes the question, analysts query PanCancer + IDC, synthesizer produces the tri-modal scorecard. Expand any step to see the NL question, tool, SQL, and row preview.
6. **Validation Scorecard** — Literature vs. genomics vs. imaging scores, revised confidence, and the actionable radiogenomic finding.
7. **Chat** — Ask *"what's the connection between autism and Alzheimer's?"* (general biomedical Q&A) or *"how often is TP53 mutated in breast cancer?"* (CRAFT text-to-SQL against PanCancer).
8. **Opportunities** — Commercial dashboard recomputed from CRAFT-measured epidemiology.
9. **Audit & export** — Filter by CRAFT agent; export the full action trail as JSON.

Offline smoke test:

```bash
cd backend
.venv/bin/python scripts/smoke_test.py "KRAS G12C lung cancer"
```

---

## Deploy

Single-project deploy with **Vercel experimental Services** — frontend at `/`, FastAPI at `/_/backend`. See **[DEPLOY.md](./DEPLOY.md)**.

Optional persistent backend: [Render](https://render.com) via `render.yaml` + `VITE_API_URL`.

---

## Project layout

```
backend/
  app/agents/           LangGraph pipeline + investigation sub-graph + CRAFT chat router
  app/services/         Literature APIs, PDF ingest, embeddings, craft_mcp.py
  app/api/routes/       REST + WebSocket (including POST …/investigate)
frontend/
  src/components/
    investigation/      Timeline, scorecard, CRAFT query cards, radiogenomics chart
    hypothesis/         Panel (auto-investigate on click), whiteboard, confidence explainer
    graph/              Force-graph with dataset node type
    audit/              Live log with CRAFT filter
  src/pages/            Landing, AutoMode
  src/layouts/          Persistent Navbar + Workspace shell
```

## Tech stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, Vite, Tailwind CSS, Framer Motion, Zustand, react-force-graph-2d, Recharts, Lucide |
| **Backend** | FastAPI, LangGraph, LangChain, ChromaDB, SQLAlchemy/SQLite, NetworkX, httpx, pypdf |
| **LLM** | Nebius Token Factory — `MiniMaxAI/MiniMax-M3` via OpenAI-compatible `/v1/chat/completions` |
| **Data intelligence** | Emergence AI CRAFT MCP — `generate_sql`, `execute_query`, `search_schema`, `resolve_term`, `generate_plotly_chart` |
| **Enterprise data** | Spider 2.0: IDC, PANCANCER_ATLAS_1, THELOOK_ECOMMERCE, BRAZILIAN_E_COMMERCE, CRYPTO, GA4, FIREBASE, GITHUB_REPOS, DEPS_DEV_V1 |
| **Literature** | Semantic Scholar, PubMed/Entrez, arXiv, user PDF upload |
| **Observability** | WebSocket audit stream, SQLite provenance, exportable JSON trail |

---

## Stakeholders

- **Researchers** — Literature synthesis, explorable knowledge graph, CRAFT-grounded Q&A, radiogenomic investigation
- **Commercial teams** — Opportunity dashboard grounded in real mutation-frequency epidemiology
- **Regulators & reviewers** — Complete audit log of every agent action, CRAFT SQL, and model invocation
