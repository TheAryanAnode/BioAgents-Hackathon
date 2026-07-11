# Deploy SynthesisOS on Vercel (experimental Services)

One Vercel project deploys **both** the Vite frontend and FastAPI backend using `experimentalServices` in `vercel.json`.

| Service | Mount | Root |
|---------|-------|------|
| Frontend | `/` | `frontend/` |
| Backend API | `/_/backend` | `backend/` |

Example API URL: `https://your-app.vercel.app/_/backend/api/health`

## 1. Vercel project setup

1. Push this repo to GitHub.
2. [vercel.com](https://vercel.com) → **Add New Project** → import repo.
3. Set **Framework Preset** to **Services** (required for `experimentalServices`).
4. Vercel reads root `vercel.json` — no manual root directory override needed.

## 2. Environment variables

Add in Vercel → **Settings → Environment Variables** (Production + Preview):

| Variable | Required | Notes |
|----------|----------|-------|
| `NEBIUS_API_KEY` | No | Enables Nebius chat + reports; demo works without it |
| `NEBIUS_MODEL` | No | Default `MiniMaxAI/MiniMax-M3` |
| `LLM_USE_IN_PIPELINE` | No | Default `false` (keep pipeline heuristic-only) |

Do **not** set `VITE_API_URL` unless overriding — production defaults to same-origin `/_/backend`.

Optional overrides:

| Variable | When to use |
|----------|-------------|
| `VITE_API_URL` | External backend (e.g. Render) instead of `/_/backend` |
| `VITE_WS_URL` | External WebSocket host |

## 3. Verify after deploy

```bash
curl https://YOUR-APP.vercel.app/_/backend/api/health
# → {"status":"ok","llm":true,"llmProvider":"nebius",...}

# Open the app, run a query (first run may take 15–40s while agents finish)
```

## 4. Local dev with services (optional)

Requires Vercel CLI ≥ 48.1.8:

```bash
npm i -g vercel
vercel dev -L
```

Or use the standard local stack:

```bash
./run.sh
```

## Notes

- **First research query** on Vercel runs the full agent pipeline inside the request (serverless cannot keep background tasks alive). Expect ~15–40s before the response returns; the UI polls session state as a fallback.
- **WebSockets** may be limited on serverless; REST polling hydrates the graph if WS drops.
- **Sessions** are in-memory per instance — fine for demos; not for multi-user production without external state.
- **Render fallback:** see `render.yaml` if you prefer a persistent backend and set `VITE_API_URL` / `VITE_WS_URL` to that URL.
