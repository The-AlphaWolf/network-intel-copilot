"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getOverview, listCells, listInvestigations, Cell, Overview, InvestigationResult } from "@/lib/api";
import { Card, CardHeader, KpiTile, Badge, EmptyState, StatDot } from "@/components/ui";
import { formatTime, healthColor } from "@/lib/format";
import { AlertTriangle, Radio, Activity, Clock } from "lucide-react";

export default function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [cells, setCells] = useState<Cell[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getOverview(), listCells(), listInvestigations(5)])
      .then(([ov, c, inv]) => {
        setOverview(ov);
        setCells(c);
        setInvestigations(inv);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const avgInvestigationMs = investigations.length
    ? investigations.reduce((s, i) => s + (i.metrics?.duration_ms || 0), 0) / investigations.length
    : 0;
  const incidentCells = cells.filter((c) => c.scenario !== "healthy");

  if (error) {
    return (
      <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">
        Failed to reach backend: {error}. Is the API running on {process.env.NEXT_PUBLIC_API_URL}?
      </div>
    );
  }

  if (loading) return <EmptyState message="Loading network overview..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Network Overview</h1>
        <p className="text-sm text-text-dim">Real-time telecom network health, powered by synthetic KPI/log data.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Active Incidents" value={overview?.active_incidents ?? "-"} sub="cells with critical anomalies" />
        <KpiTile label="Cells Monitored" value={overview?.cells_monitored ?? "-"} sub="across 4 sites" />
        <KpiTile label="Anomalies (6h)" value={overview?.anomalies_24h ?? "-"} sub="warning + critical KPI breaches" />
        <KpiTile
          label="Avg Investigation Time"
          value={avgInvestigationMs ? `${(avgInvestigationMs / 1000).toFixed(1)}s` : "-"}
          sub={`over ${investigations.length} recent runs`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Active Incidents" subtitle="Cells currently running a non-healthy scenario" />
          {incidentCells.length === 0 ? (
            <EmptyState message="No active incidents." />
          ) : (
            <div className="divide-y divide-border">
              {incidentCells.map((c) => (
                <Link
                  key={c.cell_id}
                  href={`/cells/${c.cell_id}`}
                  className="flex items-center justify-between px-4 py-3 text-sm hover:bg-surface-2"
                >
                  <div className="flex items-center gap-3">
                    <AlertTriangle className={healthColor(c.health_score) + " h-4 w-4"} />
                    <div>
                      <p className="font-mono text-text">{c.cell_id}</p>
                      <p className="text-xs text-text-faint">{c.site_name} · {c.scenario.replace(/_/g, " ")}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge tone={c.oper_state}>{c.oper_state}</Badge>
                    <span className={`font-mono text-sm ${healthColor(c.health_score)}`}>{c.health_score}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Network Health" subtitle="All cells" />
          <div className="max-h-80 divide-y divide-border overflow-y-auto">
            {cells.map((c) => (
              <div key={c.cell_id} className="flex items-center justify-between px-4 py-2 text-sm">
                <div className="flex items-center gap-2">
                  <StatDot tone={c.health_score >= 80 ? "healthy" : c.health_score >= 50 ? "warning" : "critical"} />
                  <span className="font-mono text-xs text-text-dim">{c.cell_id}</span>
                </div>
                <span className={`font-mono text-xs ${healthColor(c.health_score)}`}>{c.health_score}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Recent Investigations" right={<Link href="/investigations" className="text-xs text-cyan hover:underline">New investigation →</Link>} />
        {investigations.length === 0 ? (
          <EmptyState message="No investigations yet. Start one from the Investigations page." />
        ) : (
          <div className="divide-y divide-border">
            {investigations.map((inv) => (
              <Link
                key={inv.investigation_id}
                href={`/investigations?id=${inv.investigation_id}`}
                className="flex items-center justify-between px-4 py-3 text-sm hover:bg-surface-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-text">{inv.query}</p>
                  <p className="mt-0.5 flex items-center gap-3 text-xs text-text-faint">
                    <span className="flex items-center gap-1"><Radio className="h-3 w-3" />{inv.cell_id || "unresolved"}</span>
                    <span className="flex items-center gap-1"><Activity className="h-3 w-3" />{inv.root_causes[0]?.cause || "n/a"}</span>
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{formatTime(inv.agent_execution[0]?.timestamp)}</span>
                  </p>
                </div>
                <Badge tone={inv.status}>{inv.status}</Badge>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
