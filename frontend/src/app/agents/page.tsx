"use client";

import { useEffect, useState } from "react";
import { getAgents, AgentsResponse } from "@/lib/api";
import { Card, CardHeader, Badge, StatDot, EmptyState } from "@/components/ui";
import { formatDuration, formatTime } from "@/lib/format";
import { Bot, ArrowRight, Wrench } from "lucide-react";

export default function AgentsPage() {
  const [data, setData] = useState<AgentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAgents().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">{error}</div>;
  if (!data) return <EmptyState message="Loading..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Agent Architecture</h1>
        <p className="text-sm text-text-dim">LangGraph supervisor topology - 5 nodes, typed shared state, real tool calls.</p>
      </div>

      <Card>
        <CardHeader title="Supervisor Topology" />
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-5">
          {data.architecture.map((node, i) => {
            const status = data.last_run_status[node.id];
            return (
              <div key={node.id} className="flex items-center">
                <div className="flex-1 rounded-lg border border-border bg-surface-2 p-3">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-cyan" />
                    <span className="text-sm font-medium text-text">{node.name}</span>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-text-faint">{node.role}</p>
                  {node.tools.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {node.tools.map((t) => (
                        <span key={t} className="flex items-center gap-1 rounded bg-surface px-1.5 py-0.5 font-mono text-[9px] text-text-faint">
                          <Wrench className="h-2 w-2" />{t}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 flex items-center gap-1.5">
                    <StatDot tone={status ? (status.status === "completed" ? "healthy" : "critical") : "idle"} />
                    <span className="text-[11px] text-text-faint">{status ? `last run: ${formatDuration(status.duration_ms)}` : "no runs yet"}</span>
                  </div>
                </div>
                {i < data.architecture.length - 1 && <ArrowRight className="mx-1 hidden h-4 w-4 shrink-0 text-text-faint md:block" />}
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <CardHeader title="Last Run Status" subtitle="Per-agent status from the most recent investigation" />
        {Object.keys(data.last_run_status).length === 0 ? (
          <EmptyState message="No investigations have run yet." />
        ) : (
          <div className="divide-y divide-border">
            {Object.values(data.last_run_status).map((ev) => (
              <div key={ev.agent} className="flex items-center justify-between px-4 py-3 text-sm">
                <div className="flex items-center gap-2">
                  <StatDot tone={ev.status === "completed" ? "healthy" : "critical"} />
                  <span className="text-text">{ev.agent}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-text-faint">
                  <span>{ev.message}</span>
                  <Badge tone={ev.status}>{ev.status}</Badge>
                  <span>{formatTime(ev.timestamp)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
