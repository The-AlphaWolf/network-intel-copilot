# Network Intelligence Copilot — Implementation Roadmap

AI-powered telecom network incident investigation system.
User asks *"Investigate high latency and packet loss in cell KOL-5G-017"* → multi-agent
system pulls real KPIs/logs, retrieves cited documentation, ranks root causes, recommends fixes.

**Execution rule: build MVP end-to-end first, verify after every stage, then polish.
No TODOs in core paths. Working demo > feature completeness.**

---

## 0. Environment (verified 2026-08-19)

| Item | State | Consequence |
|---|---|---|
| Python | 3.12.10 | ok |
| Node / npm | 24.18.0 / 11.16.0 | ok, Next.js 15 |
| Docker CLI | 29.6.1 | daemon **NOT running** |
| Git | 2.55.0 | repo not initialized yet |
| LLM | OpenRouter `openai/gpt-oss-20b:free`, OpenAI-compatible, live-tested | free tier = rate limited |
| Network | huggingface.co / pypi / npm all 200 | model download ok |

### Three constraints that drive design

1. **Docker daemon down.** Native run path is primary and must be fully working:
   embedded Qdrant (`QdrantClient(path=...)`), MLflow local file store (`./mlruns`).
   `docker-compose.yml` is authored and config-validated, not required for the demo.
2. **Free-tier reasoning LLM.** Budget <= 8 LLM calls per investigation. Every LLM call
   goes through one factory with retry + timeout + response caching. `LLM_MODE=stub`
   gives deterministic templated output so tests, CI and offline demos never break.
   Do **not** depend on model-native tool calling (unreliable on free models) — LangGraph
   nodes call tools directly in Python; the LLM reasons over real tool results and returns
   structured JSON. Tool calls are real, they are just orchestrated by the graph.
3. **torch = 2.5 GB.** Default embedder is `fastembed` (ONNX) with HF model
   `BAAI/bge-small-en-v1.5` (384-dim, ~50 MB). `sentence-transformers` stays as an optional
   backend behind the same `Embedder` protocol. Tests use a deterministic fake embedder.

---

## 1. Repository layout

```
.
├─ backend/
│  ├─ app/
│  │  ├─ main.py                FastAPI app, lifespan (load data, warm Qdrant), CORS
│  │  ├─ config.py              pydantic-settings, reads .env
│  │  ├─ logging_conf.py        structlog JSON, request_id + investigation_id binding
│  │  ├─ schemas/               Pydantic v2: kpi.py cell.py investigation.py rag.py agent.py eval.py
│  │  ├─ api/v1/                health.py cells.py investigate.py knowledge.py agents.py evaluation.py
│  │  ├─ data/
│  │  │  ├─ scenarios.py        incident scenario definitions (single source of truth)
│  │  │  ├─ generator.py        seeded synthetic KPI + log generator
│  │  │  └─ store.py            load-once in-memory store, query helpers
│  │  ├─ rag/
│  │  │  ├─ embeddings.py       Embedder protocol: FastEmbed | SentenceTransformer | Fake
│  │  │  ├─ chunker.py          markdown header-aware chunking, 512 tok / 64 overlap
│  │  │  ├─ vectorstore.py      Qdrant (embedded path OR server URL from env)
│  │  │  └─ ingest.py           knowledge/*.md → chunks → vectors → collection
│  │  ├─ tools/registry.py      6 tools: plain fns + LangChain @tool wrappers
│  │  ├─ agents/
│  │  │  ├─ state.py            typed shared state (TypedDict + Pydantic payloads)
│  │  │  ├─ llm.py              LLM factory, stub mode, JSON-mode helper, call budget
│  │  │  ├─ supervisor.py analyst.py rag_agent.py root_cause.py resolution.py
│  │  │  └─ graph.py            LangGraph StateGraph + checkpointer + event emitter
│  │  └─ eval/
│  │     ├─ ground_truth.json   10 labelled incidents
│  │     ├─ metrics.py          recall@k, MRR, citation validity, faithfulness, RC accuracy
│  │     └─ run_eval.py         CLI → metrics + MLflow logging → eval_results.json
│  ├─ knowledge/                12 synthetic markdown docs
│  ├─ mcp_server/server.py      FastMCP stdio server reusing tools/registry.py
│  ├─ tests/                    pytest
│  ├─ requirements.txt, pyproject.toml, Dockerfile
├─ frontend/                    Next.js 15 App Router + TS + Tailwind v4 + Recharts
├─ docker-compose.yml           api + qdrant + mlflow + frontend
├─ .env.example
├─ README.md
└─ ROADMAP.md
```

---

## 2. Synthetic telecom data

**KPIs** (per cell, 5-min granularity, 24 h = 288 points; 14 cells ≈ 4 032 rows — trivial in memory):
`rsrp_dbm, rsrq_db, sinr_db, latency_ms, packet_loss_pct, throughput_mbps,
prb_utilization_pct, handover_success_rate_pct, drop_rate_pct, active_users`

Generator: seeded (`numpy.default_rng(42)`), per-cell baseline + diurnal sinusoid + noise,
then scenario injection over an incident window. Deterministic — same seed, same bytes.
Persisted to `backend/data_out/kpi_timeseries.csv` + `network_logs.jsonl` + `cells.json`
on first run, reloaded after.

**Topology**: 14 cells across 4 sites (KOL, DEL, MUM, BLR), each with lat/lon, band,
azimuth, and a neighbor list (used by `get_neighbor_cells` and the topology view).

**Scenarios** (5 incidents + 9 healthy/baseline cells):

| Cell | Scenario | KPI signature |
|---|---|---|
| `KOL-5G-017` | **Congestion** (primary demo) | PRB util 92–98 %, active_users 3×, latency 18→85 ms, packet_loss 0.2→2.4 %, throughput/user collapses, RSRP/SINR normal |
| `KOL-5G-004` | **Interference** | SINR 18→3 dB, RSRQ −10→−17 dB, RSRP normal, drop_rate 0.4→3.1 %, throughput down |
| `DEL-5G-009` | **Backhaul degradation** | latency 15→140 ms w/ jitter, packet_loss 0.1→6 %, throughput hard-capped flat, PRB normal |
| `MUM-5G-012` | **Poor coverage** | RSRP −85→−112 dBm, RSRQ/SINR low, drop_rate up, HO failures at cell edge |
| `BLR-5G-021` | **Handover problems** | HO success 99.2→81 %, ping-pong events, drop_rate up, neighbor relation missing |

`KOL-5G-017` deliberately shows **both** latency and loss so the root-cause ranking has to
discriminate congestion (#1) vs backhaul (#2) vs interference (#3) using PRB + RSRP evidence.
That is the demo's money shot.

**Logs**: `network_logs.jsonl` — timestamped events per cell (`severity, event_type, message,
cell_id`) from templates: PRB threshold crossings, RRC connection rejects, X2/Xn HO failures,
transport link errors, PIM/interference alarms, VSWR, licence-limit hits. ~600 lines.

---

## 3. RAG

Pipeline: `knowledge/*.md → header-aware chunker → HF embeddings → Qdrant → top-k + score
threshold → cited context block → LLM`.

**12 synthetic documents**, each with YAML frontmatter (`doc_id, title, version, category,
owner`) and an explicit banner: *"Synthetic reference documentation authored for this
demonstration system."* Topics: KPI definitions & thresholds; PRB utilization & capacity;
congestion triage runbook; uplink/downlink interference & PIM; handover parameter optimization
(A3 offset, TTT, hysteresis); transport & backhaul troubleshooting; packet loss triage;
coverage optimization & antenna tilt; load balancing and carrier aggregation; 5G NR alarm
reference; escalation matrix & SLA; capacity planning guidelines.

**Citations are never invented.** A citation is only valid if it carries a `chunk_id` that
resolves in Qdrant. `rag/` returns `Citation{doc_id, title, section, chunk_id, score, snippet}`;
the API re-validates every citation the LLM emits against the retrieved set and **drops
unresolvable ones** before responding. This is also an eval metric (citation validity).

---

## 4. Tools + MCP

All six are plain, unit-testable Python functions in `tools/registry.py`, each exported twice:
raw callable (used by graph nodes and MCP) and LangChain `@tool` (typed args schema).

| Tool | Signature | Behavior |
|---|---|---|
| `get_cell_kpis` | `(cell_id, hours=6, kpis=None)` | time series + summary stats |
| `get_cell_status` | `(cell_id)` | config, state, active alarms, health score |
| `search_network_logs` | `(cell_id=None, query=None, severity=None, hours=6, limit=50)` | filtered log events |
| `get_neighbor_cells` | `(cell_id)` | neighbor list + their health + relation status |
| `calculate_kpi_anomaly` | `(cell_id, kpi, hours=6)` | z-score vs 7-day baseline **and** threshold-rule breach → `{severity, z, deviation_pct, breached_threshold, window}` |
| `search_knowledge_base` | `(query, top_k=5, category=None)` | Qdrant vector search → cited chunks |

Anomaly math is deterministic and real (baseline mean/std per cell per KPI + spec thresholds
sourced from the KPI-definitions doc). No LLM guessing at numbers.

**MCP**: `mcp_server/server.py` uses `FastMCP` (stdio) and exposes `get_cell_kpis`,
`get_cell_status`, `search_network_logs`, `calculate_kpi_anomaly`, `search_knowledge_base`.
Same functions, zero duplication. Verified with a scripted MCP client call in tests.

---

## 5. LangGraph multi-agent system

**Supervisor architecture**, typed shared state, real tool calls.

```
        ┌──────────────┐
   ───▶ │  SUPERVISOR  │◀─────────────┐
        └──────┬───────┘              │ (returns after each agent)
    routes to next unfinished stage   │
   ┌─────┬─────┴─────┬──────────┐     │
   ▼     ▼           ▼          ▼     │
 ANALYST  RAG    ROOT_CAUSE  RESOLUTION
   └──────┴──────────┴──────────┴─────┘ → END (supervisor writes summary)
```

`state.py` — `InvestigationState(TypedDict, total=False)`:
`investigation_id, query, cell_id, time_window_hours, plan, completed[], kpi_snapshot,
anomalies[], evidence[], log_events[], neighbors[], citations[], hypotheses[],
recommendations[], agent_events[], errors[], summary, llm_calls`

Node responsibilities:

- **Supervisor** — 1 LLM call up front: parse query → `cell_id`, intent, time window, plan.
  Then pure routing on `completed` (deterministic guardrail: max 8 super-steps, no infinite
  loops). 1 final LLM call for the executive summary.
- **Network Analyst** — real tool calls: `get_cell_status`, `get_cell_kpis`,
  `calculate_kpi_anomaly` across all 10 KPIs, `search_network_logs`, `get_neighbor_cells`.
  1 LLM call to interpret the anomaly table into evidence statements.
- **RAG Agent** — 1 LLM call generates 2–3 targeted queries from the anomaly signature →
  real `search_knowledge_base` calls → dedupe/rank → cited context. 1 LLM call to synthesize
  a grounded, citation-tagged findings block.
- **Root Cause Agent** — 1 LLM call correlating anomalies + logs + neighbors + doc evidence
  into ranked hypotheses with `confidence 0–1`, supporting/contradicting evidence, and
  citations. Post-processed by a deterministic scorer that blends LLM confidence with
  rule-based signature matching (so confidence is never pure vibes).
- **Resolution Agent** — 1 LLM call → prioritized actions with `{action, category, priority,
  expected_impact, risk, owner_team, estimated_time, citations}`.

Total: ~7 LLM calls / investigation, inside the free-tier budget.

Every node emits `AgentEvent{agent, status, message, tools_used, duration_ms, timestamp}` →
that array powers the live frontend timeline, and streams over SSE via `graph.astream`.

Failure policy: any node exception is caught, recorded in `errors[]`, marked completed, graph
continues. A partial investigation is still returned. No 500s from agent failures.

---

## 6. API

`POST /api/v1/investigate` — body `{query, cell_id?, time_window_hours?}` → `InvestigationResult`:

```
investigation_id, query, cell_id, status, started_at, duration_ms,
summary,
kpi_anomalies[]   { kpi, current, baseline, deviation_pct, z_score, severity, series[] }
evidence[]        { source: kpi|log|neighbor|doc, title, detail, severity, timestamp }
root_causes[]     { rank, cause, category, confidence, explanation, supporting_evidence[], citations[] }
recommendations[] { priority, action, category, expected_impact, risk, owner_team, eta, citations[] }
citations[]       { doc_id, title, section, chunk_id, score, snippet }
agent_execution[] { agent, status, message, tools_used[], duration_ms, timestamp }
metrics           { llm_calls, tools_called, tokens_estimate, retrieval_hits }
```

Also: `GET /api/v1/investigate/stream` (SSE live timeline), `GET /api/v1/investigate/{id}`,
`GET /api/v1/investigations` (recent), `GET /api/v1/health`, `GET /api/v1/health/system`
(component-by-component: Qdrant, embedder, LLM, data store, MLflow),
`GET /api/v1/cells | /cells/{id} | /cells/{id}/kpis | /cells/{id}/neighbors | /topology`,
`GET /api/v1/knowledge/documents`, `POST /api/v1/knowledge/search`,
`GET /api/v1/agents` (architecture + status), `GET /api/v1/evaluation/latest`.

---

## 7. Frontend — enterprise telecom dashboard (not a chat clone)

Next.js 15 App Router, TypeScript, Tailwind v4, Recharts, lucide-react. No component library.

**Design language**: base `#080D18` / surface `#0F1626` / border `#1E293B`, accent cyan
`#22D3EE` + blue `#3B82F6`, status amber/red/emerald. Inter for UI, JetBrains Mono for KPI
numerals and cell IDs. Motion: 150–200 ms fades and a single pulsing "active" dot on the
running agent — nothing else moves.

Persistent left sidebar: Overview · Investigations · Cells · Knowledge Base · Agents ·
Evaluation · System Health. Top bar: environment badge, backend health dot, clock.

- **Overview** — 4 KPI cards (Active Incidents, Cells Monitored, Anomalies 24 h, Avg
  Investigation Time), incident table, network health strip, recent investigations.
- **Investigations** — large query input with scenario chips → live agent timeline (SSE,
  per-agent status + tools used + duration) → results: anomaly charts (actual vs baseline
  band), root-cause ranking with confidence bars, evidence cards, citation cards linking to
  the KB doc, recommendation cards by priority.
- **Cells** — sortable table, detail drawer with multi-KPI charts, plus an SVG topology view
  (sites + neighbor edges, colored by health).
- **Knowledge Base** — document list + live semantic search with scores and snippets.
- **Agents** — architecture graph of the supervisor topology, per-agent role/tools/status.
- **Evaluation** — metrics from `eval_results.json` + MLflow run table.
- **System Health** — per-component status, versions, latencies, data stats.

---

## 8. Evaluation / MLOps

`eval/ground_truth.json`: 10 labelled incidents → `{query, cell_id, true_root_cause_category,
acceptable_causes[], relevant_doc_ids[], expected_action_keywords[]}`.

Metrics (`eval/metrics.py`, all unit-tested pure functions):
- **Retrieval**: recall@5, precision@5, MRR against `relevant_doc_ids`.
- **Citation correctness**: fraction of emitted citations resolving to a real retrieved chunk.
- **Faithfulness**: LLM-as-judge over (claim, cited chunk); lexical-overlap fallback in stub mode.
- **Root-cause accuracy**: top-1 and top-3 category match; mean confidence on correct answers.

`python -m app.eval.run_eval` runs the suite, logs params (embed model, chunk size, top_k,
LLM, prompt version) + metrics + `eval_results.json` artifact to MLflow (local `./mlruns`,
UI on :5000), and writes the JSON the frontend Evaluation page reads.

---

## 9. Engineering quality

Pydantic v2 schemas everywhere · full type hints · `pydantic-settings` + `.env` ·
structlog JSON logs with `investigation_id` binding · typed exceptions + FastAPI handlers ·
modular layering (api → agents → tools → data/rag, never the reverse).

**pytest**, ~30 tests: generator determinism · anomaly math edge cases · each of the 6 tools ·
chunker · vector store with fake embedder · full graph run in `LLM_MODE=stub` · API contract
tests via `TestClient` · MCP tool round-trip · every eval metric.

`docker-compose.yml`: `api` (8000) · `qdrant` (6333) · `mlflow` (5000) · `frontend` (3000),
healthchecks + named volumes. Validated with `docker compose config`; runtime start depends on
the user launching Docker Desktop. **Native path stays the supported demo path.**

---

## 10. Build order — verify after every stage

| # | Stage | Done when |
|---|---|---|
| 1 | Scaffold + config + logging + **synthetic data** | `python -m app.data.generator` writes CSV/JSONL; determinism test green |
| 2 | **RAG + Qdrant** | 12 docs ingested; `search_knowledge_base("PRB congestion")` returns sane cited chunks |
| 3 | **Tools + LangGraph agents** | `python -m app.agents.graph --query "..."` prints full ranked result in both stub and live LLM mode |
| 4 | **API** | `POST /api/v1/investigate` returns the full schema; `/docs` clean; SSE stream emits events |
| 5 | **Frontend** | all 7 pages build and render live backend data; investigation runs end to end in the browser |
| 6 | **MCP + MLflow + tests** | MCP client lists/calls tools; `run_eval` logs an MLflow run; `pytest` green |
| 7 | **Polish** | README, `.env.example`, compose validated, error/empty/loading states, final full-app run |

**Stage gate: run it, fix errors, then continue. No stage is "done" while it throws.**

---

## 11. Risks and their mitigations

| Risk | Mitigation |
|---|---|
| Free LLM rate-limit / 429 | call budget ≤ 8, retry w/ backoff, `LLM_MODE=stub` deterministic fallback, cached responses |
| `gpt-oss-20b` returns `reasoning` and null `content` | generous `max_tokens`, low reasoning effort, JSON extraction helper tolerant of prose wrappers |
| Model refuses / emits malformed JSON | strict parse → repair pass → rule-based fallback per node; investigation never fails |
| Docker daemon offline | embedded Qdrant + local MLflow; compose only config-validated |
| First-run model download latency | ~50 MB fastembed ONNX, downloaded once at ingest, cached; startup logs progress |
| Windows path/encoding issues | `pathlib` everywhere, `encoding="utf-8"` on every file op |

## 12. Naming

Product name: **Network Intelligence Copilot**. No employer or vendor name appears anywhere
in code, docs, UI, comments, or commit messages. Cell IDs and documents are generic-synthetic.
