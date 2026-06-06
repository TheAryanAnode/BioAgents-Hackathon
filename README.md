# SynthesisOS — Autonomous Research Agent

> Track 02 · Autonomous Research — literature synthesis, hypothesis generation, and evidence tracking.

SynthesisOS is a full-stack autonomous research assistant. Give it a research
domain and a team of agents continuously ingests scientific literature (public
APIs **and** your own uploaded PDFs), builds an interactive knowledge graph,
generates novel hypotheses from structural gaps in that graph, tracks supporting
and contradicting evidence, and translates findings into commercial
opportunities — all while logging every action for full auditability.

It is built to serve three stakeholders at once:

- **Researchers** — fast literature synthesis, an explorable paper/concept map, and grounded Q&A.
- **Commercial teams** — an opportunity dashboard that surfaces hidden patient subgroups and whitespace.
- **Regulators** — a complete, exportable audit log of every API call, model invocation, and transformation.

---

## Why it stands out

- **Autonomous, not just search.** The hypothesis agent finds *open triangles* in the knowledge graph — pairs of well-connected concepts that the literature never directly links — and proposes testable mechanisms a keyword search would never surface.
- **Private corpus + public literature in one layer.** Uploaded PDFs are parsed, embedded, and merged into the *same* vector index and knowledge graph as API-fetched papers, so they immediately participate in hypotheses, evidence, and chat citations.
- **Radical transparency.** Every agent action streams to a live, exportable audit log over WebSocket.
- **Runs with or without an API key.** With a Google Gemini key it uses Gemini for extraction, classification, and Q&A. Without one, it falls back to deterministic heuristics and a curated corpus so the demo *always* works offline.
- **Bold Typography design system.** A confident, editorial dark UI — sharp edges, extreme type scale, a single vermillion accent.

---

## Architecture

```
React + Vite (Bold Typography UI)
   │  REST + WebSocket  (Vite proxy → :8000)
   ▼
FastAPI  ──►  LangGraph orchestrator
                 │  ingestion → analysis → graph → hypothesis → evidence → commercial
                 ▼
   Semantic Scholar · PubMed · arXiv · user PDFs · Google Gemini
                 ▼
   ChromaDB (vectors) · SQLite (provenance/audit) · NetworkX (graph compute)
```

The multi-agent pipeline:

| Agent | Responsibility |
|-------|----------------|
| Ingestion | Fetch papers (S2 / PubMed / arXiv) + ingest user PDFs; chunk and embed into the corpus |
| Analysis | Extract biomedical entities and relations (Gemini, or a domain lexicon fallback) |
| Graph Builder | Build the NetworkX graph, compute centrality, detect clusters, export to the client |
| Hypothesis | Detect structural gaps (open triangles) and generate testable hypotheses |
| Evidence | Retrieve relevant chunks, classify stance (support / contradict / neutral), score confidence over time |
| Commercial | Estimate patient subgroups, unmet need, whitespace, and ROI; build the dashboard |

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
uv venv --python 3.12              # or: python3.12 -m venv .venv
uv pip install -r requirements.txt # or: .venv/bin/pip install -r requirements.txt
cp .env.example .env               # optional: add GOOGLE_API_KEY for full Gemini mode
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

The server prints its mode on startup, e.g. `gemini=off (demo mode) embeddings=hashing`.

#### 2. Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` and `/ws` to the backend on `:8000`.

**If you see `vite: command not found`:** your environment may skip devDependencies (e.g. `NODE_ENV=production`). Run `npm install --include=dev` (or `NODE_ENV=development npm install`). The `npm run` scripts invoke Vite via `node ./node_modules/vite/...` so a working `node` is enough once `vite` is installed.

> No API key? Everything still runs in deterministic demo mode. Add a
> `GOOGLE_API_KEY` to `backend/.env` to enable Gemini for **chat** and **reports**.
>
> **Free-tier rate limits:** Gemini free tier allows ~5 requests/minute. By default
> `GEMINI_USE_IN_PIPELINE=false` so the research graph/hypothesis pipeline uses
> fast heuristics and does not burn your quota. Chat and “Generate full report” use Gemini.

---

## Demo flow (≈3 minutes)

1. **Query** — On the landing page, enter `autism genomics` (or click the example chip).
2. **Live ingestion** — Open the Audit toggle (top-right). Watch agents fetch from Semantic Scholar, PubMed, and arXiv in real time as paper nodes animate into the graph.
3. **Explore the graph** — Concepts are vermillion, papers white, your uploads green. Click a gene node (e.g. `SCN2A`) to open its detail panel; filter by year or source.
4. **Upload a paper** — Click **Upload** on the graph toolbar and drop a PDF. The audit log shows extract → embed → link steps, and a green `USER`-tagged node joins the nearest cluster.
5. **Hypotheses** — Switch to the Hypotheses tab. Each card shows a confidence meter; the chart tracks confidence over time. Select one to see its evidence stack (support vs contradict), which can cite your uploaded PDF.
6. **Opportunities** — The dashboard scores patient subgroups by unmet need, whitespace, and ROI, with a research-activity trend chart and a stratification breakdown.
7. **Chat** — Ask "What connects SCN2A to epilepsy?" — the agent answers with clickable citations that jump back to nodes in the graph.
8. **Audit & export** — Expand the audit log and export the full action trail as JSON for compliance.

A scripted, offline end-to-end check:

```bash
cd backend
.venv/bin/python scripts/smoke_test.py "autism genomics"
```

---

## Project layout

```
backend/   FastAPI app, LangGraph agents, services (literature, PDF, embeddings), SQLite + ChromaDB
frontend/  React + Vite + Tailwind, force-graph visualization, dashboard, chat, audit log
```

## Tech stack

- **Frontend:** React 18, Vite, Tailwind CSS, react-force-graph-2d, Recharts, Framer Motion, Zustand, Lucide.
- **Backend:** FastAPI, LangGraph, LangChain + Gemini, ChromaDB, SQLAlchemy/SQLite, NetworkX, pypdf, httpx.
- **Data sources:** Semantic Scholar, PubMed/Entrez, arXiv (all free tier).
