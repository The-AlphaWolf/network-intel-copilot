# Network Intelligence Copilot

AI-powered telecom network incident investigation system. Describe a network
problem in plain language — *"Investigate high latency and packet loss in
cell KOL-5G-017"* — and a LangGraph supervisor multi-agent system pulls real
KPI/log data, retrieves cited technical documentation via RAG, ranks root
causes, and recommends remediation. Built as a portfolio project demonstrating
GenAI/agentic engineering: LangGraph, RAG over Qdrant, MCP, MLflow evaluation,
and a production-shaped FastAPI + Next.js stack.

All data is synthetic. No real network, operator, or vendor is represented.

## Screenshot tour

Not included as static images here — run it locally (2 commands, below) and
it's live in under a minute.

## Architecture

```
Next.js frontend  ──HTTP/SSE──▶  FastAPI  ──▶  LangGraph supervisor
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                 Network Analyst          RAG Agent            (routes to)
                        │                     │            Root Cause Agent
                 6 tools over            Qdrant vector          │
                 synthetic KPI/          search over      Resolution Agent
                 log/topology data       12 knowledge docs
```

- **Supervisor** parses the request (cell id, time window), routes to each
  specialist in sequence, writes the final executive summary.
- **Network Analyst** calls `get_cell_status`, `get_cell_kpis`,
  `calculate_kpi_anomaly` (×10 KPIs), `search_network_logs`,
  `get_neighbor_cells` — real function calls against the generated dataset.
- **RAG Agent** turns the anomaly signature into 2-3 targeted queries,
  retrieves cited chunks via `search_knowledge_base`, synthesizes findings.
  Citations are re-validated against what was actually retrieved before
  reaching the API response — a citation that doesn't resolve is dropped,
  never fabricated.
- **Root Cause Agent** blends the LLM's judgment with a deterministic
  KPI-signature rule scorer (congestion / interference / backhaul /
  coverage / handover), so confidence isn't pure model vibes.
- **Resolution Agent** turns the top hypothesis into prioritized,
  citation-grounded remediation actions.

Full plan in [ROADMAP.md](ROADMAP.md).

## Stack

Python · FastAPI · LangGraph · LangChain · Hugging Face embeddings
(`fastembed` / `BAAI/bge-small-en-v1.5`) · Qdrant · MCP · MLflow · pytest ·
Next.js 16 · TypeScript · Tailwind v4 · Recharts · Docker Compose

## Quick start (native, no Docker required)

```bash
# 1. backend
cd backend
python -m venv ../.venv && source ../.venv/Scripts/activate   # or ../.venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cd ..
cp .env.example .env   # defaults work as-is (LLM_MODE=stub, embedded Qdrant)

# 2. generate data + ingest knowledge base (also happens automatically on first API startup)
cd backend
python -m app.data.generator
python -m app.rag.ingest

# 3. run the API
python -m uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs
```

```bash
# 4. frontend, in a second terminal
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

Open the app, go to **Investigations**, click one of the scenario chips (or
type your own query naming a cell like `KOL-5G-017`), watch the live agent
timeline, and read the result.

### Live LLM mode

Default `LLM_MODE=stub` runs a fully deterministic rule-based pipeline — zero
external calls, instant, reproducible. To use a real LLM, set in `.env`:

```
LLM_MODE=live
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1   # any OpenAI-compatible endpoint
OPENAI_MODEL=your-model
```

Verified working end to end against a free-tier OpenRouter model — expect
~3-4 minutes per investigation on a free tier (rate-limited, ~6-7 calls);
faster/paid models are proportionally quicker. The SSE stream shows live
progress either way. If the LLM fails or times out, every agent falls back
to its rule-based logic — an investigation never hard-fails.

## Docker Compose

```bash
docker compose up --build
```

Starts `qdrant` (6333), `mlflow` (5000), `api` (8000), `frontend` (3000).
Uses `LLM_MODE=stub` by default; set `OPENAI_API_KEY`/`LLM_MODE=live` in a
root `.env` file to enable live mode (compose reads it automatically).

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

78 tests: synthetic data determinism, anomaly z-score/threshold logic, all 6
tools, the chunker, an isolated vector store instance, full LangGraph runs
(stub mode) for every incident scenario, citation-validity checks, FastAPI
contract tests, and every eval metric. Runs in ~10s, fully isolated from dev
data (its own fake embedder + Qdrant collection).

## Evaluation

Embedded Qdrant only supports one process at a time, so **stop the API
server first** (or set `QDRANT_URL=http://localhost:6333` against a running
Qdrant server/docker-compose to allow both at once):

```bash
cd backend
python -m app.eval.run_eval
```

Runs the 10-case ground-truth dataset (all 5 scenarios, 2 phrasings each)
through the real pipeline, computes retrieval recall/precision/MRR, citation
correctness, faithfulness, and root-cause accuracy, logs everything to
MLflow (`http://localhost:5000` if using Docker Compose, or a local SQLite
store otherwise), and writes `backend/data_out/eval_results.json`, which the
frontend's **Evaluation** page reads directly.

## MCP server

```bash
cd backend
python -m mcp_server.server
```

Exposes `get_cell_kpis`, `get_cell_status`, `search_network_logs`,
`calculate_kpi_anomaly`, `search_knowledge_base` over stdio — the exact same
functions the LangGraph agents call, wired to any MCP client. Point an MCP
client's config at `python -m mcp_server.server` (working directory:
`backend/`).

## API

`POST /api/v1/investigate` — full structured result: summary, KPI anomalies,
evidence, ranked root causes with confidence, citations, recommendations,
and per-agent execution trace.

`GET /api/v1/investigate/stream?query=...` — same investigation over
Server-Sent Events, for a live agent timeline.

Full interactive reference at `/docs` once the API is running. Also see
`/api/v1/cells`, `/topology`, `/knowledge/documents`, `/knowledge/search`,
`/agents`, `/evaluation/latest`, `/health/system`.

## Synthetic data

14 cells across 4 sites, 10 KPIs (RSRP, RSRQ, SINR, latency, packet loss,
throughput, PRB utilization, handover success rate, drop rate, active
users) at 5-minute granularity over 24h, plus ~100 network log events.
Deterministically seeded (`DATA_SEED=42`) — same seed, same bytes.

Five injected incidents, each with a distinct, discriminable KPI signature:

| Cell | Scenario | Signature |
|---|---|---|
| `KOL-5G-017` | Congestion | PRB util >85%, 3× active users, latency/loss up, **RSRP/SINR normal** |
| `KOL-5G-004` | Interference | SINR/RSRQ collapse, **RSRP stays stable** |
| `DEL-5G-009` | Backhaul degradation | Latency/jitter/loss up, **PRB normal**, throughput hard-capped |
| `MUM-5G-012` | Poor coverage | RSRP/RSRQ/SINR degrade **together** |
| `BLR-5G-021` | Handover problems | HO success down, missing neighbor relation |

The bolded clauses are exactly the discriminators documented in
`backend/knowledge/*.md` and encoded in the root-cause agent's rule scorer —
the system reasons the way the runbooks say to, not by peeking at the
injected scenario label.

## Project layout

See [ROADMAP.md](ROADMAP.md) for the full build plan and design rationale.

```
backend/
  app/
    agents/     LangGraph supervisor + 5 nodes, typed shared state, LLM client
    api/v1/     FastAPI routers
    data/       synthetic generator, scenario definitions, query store
    eval/       ground truth, metrics, MLflow run script
    rag/        chunker, embeddings, Qdrant vector store, ingest
    schemas/    Pydantic models
    tools/      the 6 investigation tools
  knowledge/    12 synthetic technical reference docs
  mcp_server/   MCP stdio server
  tests/        pytest suite
frontend/
  src/app/      Next.js App Router pages (7 sidebar sections)
  src/components/
  src/lib/      typed API client
```
