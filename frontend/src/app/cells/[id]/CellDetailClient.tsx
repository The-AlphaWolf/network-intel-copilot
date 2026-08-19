"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getCell, getCellKpis, getCellAnomalies, getCellNeighbors, Cell, KpiSeriesResponse, Anomaly, NeighborRelation } from "@/lib/api";
import { Card, CardHeader, Badge, KpiTile, EmptyState } from "@/components/ui";
import { formatKpiName, healthColor } from "@/lib/format";
import { ArrowLeft } from "lucide-react";

const CHART_KPIS = ["prb_utilization_pct", "latency_ms", "packet_loss_pct", "sinr_db", "rsrp_dbm", "handover_success_rate_pct"];

export function CellDetailClient({ cellId }: { cellId: string }) {
  const [cell, setCell] = useState<Cell | null>(null);
  const [kpis, setKpis] = useState<KpiSeriesResponse | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [neighbors, setNeighbors] = useState<NeighborRelation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getCell(cellId), getCellKpis(cellId, 24), getCellAnomalies(cellId, 6), getCellNeighbors(cellId)])
      .then(([c, k, a, n]) => { setCell(c); setKpis(k); setAnomalies(a); setNeighbors(n); })
      .catch((e) => setError(e.message));
  }, [cellId]);

  if (error) return <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">{error}</div>;
  if (!cell) return <EmptyState message="Loading cell..." />;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/cells" className="flex items-center gap-1 text-xs text-text-faint hover:text-cyan"><ArrowLeft className="h-3 w-3" />Back to cells</Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="font-mono text-xl font-semibold text-text">{cell.cell_id}</h1>
          <Badge tone={cell.oper_state}>{cell.oper_state}</Badge>
        </div>
        <p className="text-sm text-text-dim">{cell.site_name} · {cell.band} · {cell.technology} · scenario: {cell.scenario.replace(/_/g, " ")}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiTile label="Health Score" value={cell.health_score} sub={cell.oper_state} />
        <KpiTile label="Active Alarms" value={new Set(cell.active_alarms).size} sub={cell.admin_state} />
        <KpiTile label="Neighbors" value={neighbors.length} sub={`${neighbors.filter(n => n.relation_status !== "active").length} degraded/missing`} />
      </div>

      <Card>
        <CardHeader title="KPI Anomalies" subtitle="Last 6 hours vs diurnal-adjusted baseline" />
        <div className="divide-y divide-border">
          {anomalies.map((a) => (
            <div key={a.kpi} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span className="text-text-dim">{formatKpiName(a.kpi)}</span>
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-text-faint">current {a.current ?? "-"}</span>
                <span className="font-mono text-xs text-text-faint">z={a.z_score}</span>
                <Badge tone={a.severity}>{a.severity}</Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {CHART_KPIS.map((kpi) => {
          const series = kpis?.series[kpi];
          if (!series) return null;
          const data = series.map((p) => ({ t: new Date(p.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), v: p.value }));
          return (
            <Card key={kpi}>
              <CardHeader title={formatKpiName(kpi)} subtitle="24h" />
              <div className="h-48 px-2 py-3">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="t" stroke="#5b6b83" fontSize={10} interval={Math.floor(data.length / 6)} />
                    <YAxis stroke="#5b6b83" fontSize={10} width={40} />
                    <Tooltip contentStyle={{ background: "#0f1626", border: "1px solid #1e293b", borderRadius: 6, fontSize: 12 }} />
                    <Line type="monotone" dataKey="v" stroke="#22d3ee" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader title="Neighbor Relations" />
        <div className="divide-y divide-border">
          {neighbors.length === 0 ? <EmptyState message="No neighbors configured." /> : neighbors.map((n) => (
            <div key={n.neighbor_id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <Link href={`/cells/${n.neighbor_id}`} className="font-mono text-cyan hover:underline">{n.neighbor_id}</Link>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-faint">{n.distance_km} km</span>
                <span className={`font-mono text-xs ${healthColor(n.neighbor_health_score)}`}>{n.neighbor_health_score}</span>
                <Badge tone={n.relation_status === "active" ? "healthy" : "critical"}>{n.relation_status}</Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
