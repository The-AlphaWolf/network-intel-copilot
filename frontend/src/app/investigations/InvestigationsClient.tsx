"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell as RCell, ResponsiveContainer } from "recharts";
import { apiUrl, getInvestigation, AgentEvent, InvestigationResult } from "@/lib/api";
import { Card, CardHeader, Badge, EmptyState, StatDot } from "@/components/ui";
import { formatKpiName, formatDuration } from "@/lib/format";
import { Search, Loader2, BookOpen, FileText, Wrench } from "lucide-react";

const SCENARIO_CHIPS = [
  { label: "Congestion · KOL-5G-017", query: "Investigate high latency and packet loss in cell KOL-5G-017" },
  { label: "Interference · KOL-5G-004", query: "SINR is degrading on cell KOL-5G-004, please investigate" },
  { label: "Backhaul · DEL-5G-009", query: "High latency and packet loss reported for cell DEL-5G-009" },
  { label: "Coverage · MUM-5G-012", query: "Users complaining about poor signal in cell MUM-5G-012" },
  { label: "Handover · BLR-5G-021", query: "Handover failures happening on cell BLR-5G-021" },
];

const AGENT_LABELS: Record<string, string> = {
  supervisor: "Supervisor",
  network_analyst: "Network Analyst",
  rag_agent: "RAG Agent",
  root_cause_agent: "Root Cause Agent",
  resolution_agent: "Resolution Agent",
};

const SEV_COLOR: Record<string, string> = { critical: "#f87171", warning: "#fbbf24", normal: "#34d399" };

export default function InvestigationsClient() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const id = searchParams.get("id");
    if (id) {
      getInvestigation(id).then(setResult).catch((e) => setError(e.message));
    }
    return () => esRef.current?.close();
  }, [searchParams]);

  function runInvestigation(q: string) {
    if (!q.trim() || running) return;
    setError(null);
    setResult(null);
    setEvents([]);
    setRunning(true);
    esRef.current?.close();

    const url = apiUrl(`/investigate/stream?query=${encodeURIComponent(q)}`);
    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener("agent_event", (e) => {
      const ev = JSON.parse((e as MessageEvent).data) as AgentEvent;
      setEvents((prev) => [...prev, ev]);
    });
    es.addEventListener("result", (e) => {
      setResult(JSON.parse((e as MessageEvent).data) as InvestigationResult);
    });
    es.addEventListener("error", (e) => {
      const data = (e as MessageEvent).data;
      if (data) {
        try {
          setError(JSON.parse(data).error);
        } catch {
          setError("Stream error");
        }
      }
    });
    es.addEventListener("done", () => {
      setRunning(false);
      es.close();
    });
  }

  const anomalyData = result?.kpi_anomalies
    .filter((a) => a.severity !== "normal")
    .sort((a, b) => Math.abs(b.deviation_pct) - Math.abs(a.deviation_pct))
    .map((a) => ({ name: formatKpiName(a.kpi), value: Math.round(a.deviation_pct * 10) / 10, severity: a.severity }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Investigations</h1>
        <p className="text-sm text-text-dim">Describe the network problem in plain language. The multi-agent system will investigate.</p>
      </div>

      <Card className="p-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runInvestigation(query)}
              placeholder="e.g. Investigate high latency and packet loss in cell KOL-5G-017"
              className="w-full rounded-md border border-border bg-surface-2 py-3 pl-10 pr-3 text-sm text-text placeholder:text-text-faint focus:border-cyan focus:outline-none"
            />
          </div>
          <button
            onClick={() => runInvestigation(query)}
            disabled={running}
            className="flex items-center gap-2 rounded-md bg-cyan px-4 py-3 text-sm font-medium text-bg hover:bg-cyan/90 disabled:opacity-50"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Investigate
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SCENARIO_CHIPS.map((c) => (
            <button
              key={c.label}
              onClick={() => { setQuery(c.query); runInvestigation(c.query); }}
              disabled={running}
              className="rounded-full border border-border bg-surface-2 px-3 py-1 text-xs text-text-dim hover:border-cyan hover:text-cyan disabled:opacity-50"
            >
              {c.label}
            </button>
          ))}
        </div>
      </Card>

      {error && (
        <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-3 text-sm text-red">{error}</div>
      )}

      {(events.length > 0 || running) && (
        <Card>
          <CardHeader title="Agent Execution Timeline" subtitle="Live multi-agent investigation" />
          <div className="space-y-0 divide-y divide-border">
            {events.map((ev, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3 fade-in">
                <StatDot tone={ev.status === "completed" ? "healthy" : ev.status === "failed" ? "critical" : "warning"} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text">{AGENT_LABELS[ev.agent] || ev.agent}</span>
                    <span className="font-mono text-xs text-text-faint">{formatDuration(ev.duration_ms)}</span>
                  </div>
                  <p className="mt-0.5 text-xs text-text-dim">{ev.message}</p>
                  {ev.tools_used.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {ev.tools_used.map((t) => (
                        <span key={t} className="flex items-center gap-1 rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-faint">
                          <Wrench className="h-2.5 w-2.5" />{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {running && (
              <div className="flex items-center gap-2 px-4 py-3 text-xs text-text-faint">
                <span className="pulse-dot inline-block h-2 w-2 rounded-full bg-cyan" />
                waiting for next agent...
              </div>
            )}
          </div>
        </Card>
      )}

      {result && (
        <div className="space-y-4 fade-in">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text">Executive Summary</h3>
              <div className="flex items-center gap-2">
                <Badge tone={result.status}>{result.status}</Badge>
                {result.cell_id && <span className="font-mono text-xs text-text-dim">{result.cell_id}</span>}
              </div>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-text-dim">{result.summary}</p>
            <div className="mt-3 flex gap-4 text-xs text-text-faint">
              <span>{result.metrics.llm_calls} LLM calls</span>
              <span>{result.metrics.tools_called} tool calls</span>
              <span>{result.metrics.retrieval_hits} citations retrieved</span>
              <span>{formatDuration(result.metrics.duration_ms)} total</span>
            </div>
            {result.errors.length > 0 && (
              <div className="mt-3 rounded border border-amber/30 bg-amber/5 px-3 py-2 text-xs text-amber">
                {result.errors.join(" · ")}
              </div>
            )}
          </Card>

          {anomalyData && anomalyData.length > 0 && (
            <Card>
              <CardHeader title="KPI Anomalies" subtitle="Deviation from baseline, %" />
              <div className="h-64 px-2 py-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={anomalyData} layout="vertical" margin={{ left: 12, right: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" stroke="#5b6b83" fontSize={11} />
                    <YAxis type="category" dataKey="name" stroke="#5b6b83" fontSize={11} width={140} />
                    <Tooltip
                      contentStyle={{ background: "#0f1626", border: "1px solid #1e293b", borderRadius: 6, fontSize: 12 }}
                      formatter={(v) => [`${v}%`, "deviation"]}
                    />
                    <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                      {anomalyData.map((d, i) => (
                        <RCell key={i} fill={SEV_COLOR[d.severity]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          <Card>
            <CardHeader title="Root Cause Ranking" subtitle="Confidence-weighted hypotheses" />
            {result.root_causes.length === 0 ? (
              <EmptyState message="No root cause determined." />
            ) : (
              <div className="divide-y divide-border">
                {result.root_causes.map((rc) => (
                  <div key={rc.rank} className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-2 font-mono text-[11px] text-text-dim">{rc.rank}</span>
                        <span className="text-sm font-medium text-text">{rc.cause}</span>
                      </div>
                      <span className="font-mono text-sm text-cyan">{Math.round(rc.confidence * 100)}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                      <div className="h-full rounded-full bg-gradient-to-r from-blue to-cyan" style={{ width: `${rc.confidence * 100}%` }} />
                    </div>
                    <p className="mt-2 text-xs text-text-dim">{rc.explanation}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title="Evidence" subtitle={`${result.evidence.length} items from KPIs, logs, neighbors`} />
              <div className="max-h-96 divide-y divide-border overflow-y-auto">
                {result.evidence.length === 0 ? <EmptyState message="No evidence collected." /> : result.evidence.map((ev, i) => (
                  <div key={i} className="px-4 py-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-text">{ev.title}</span>
                      <Badge tone={ev.severity}>{ev.severity}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-text-faint">{ev.detail}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="Source Citations" subtitle={`${result.citations.length} retrieved passages, RAG-verified`} />
              <div className="max-h-96 divide-y divide-border overflow-y-auto">
                {result.citations.length === 0 ? <EmptyState message="No citations retrieved." /> : result.citations.map((c) => (
                  <div key={c.chunk_id} className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-text">
                      <BookOpen className="h-3 w-3 text-cyan" />
                      {c.title} <span className="text-text-faint">· {c.section}</span>
                    </div>
                    <p className="mt-1 text-xs text-text-faint line-clamp-2">{c.snippet}</p>
                    <p className="mt-1 font-mono text-[10px] text-text-faint">score {c.score.toFixed(3)}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader title="Recommended Actions" subtitle="Prioritized, citation-grounded remediation" />
            <div className="divide-y divide-border">
              {result.recommendations.length === 0 ? <EmptyState message="No recommendations generated." /> : result.recommendations.map((r, i) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2">
                      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-cyan" />
                      <div>
                        <p className="text-sm text-text">{r.action}</p>
                        <p className="mt-1 text-xs text-text-faint">{r.expected_impact}</p>
                        <div className="mt-1.5 flex flex-wrap gap-2 text-[11px] text-text-faint">
                          <span>{r.owner_team}</span>
                          <span>· {r.estimated_time}</span>
                          <span>· risk: {r.risk}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <Badge tone={r.priority === "P1" ? "critical" : r.priority === "P2" ? "warning" : "normal"}>{r.priority}</Badge>
                      <span className="text-[10px] text-text-faint">{r.category}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
