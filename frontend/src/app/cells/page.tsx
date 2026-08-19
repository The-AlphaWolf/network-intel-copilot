"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listCells, getTopology, Cell, Topology } from "@/lib/api";
import { Card, CardHeader, Badge, StatDot } from "@/components/ui";
import { healthColor } from "@/lib/format";
import { TopologyView } from "@/components/TopologyView";

export default function CellsPage() {
  const [cells, setCells] = useState<Cell[]>([]);
  const [topology, setTopology] = useState<Topology | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listCells(), getTopology()])
      .then(([c, t]) => { setCells(c); setTopology(t); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">{error}</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Cells</h1>
        <p className="text-sm text-text-dim">{cells.length} cells across {topology ? Object.keys(topology.sites).length : "-"} sites</p>
      </div>

      <Card>
        <CardHeader title="Cell Inventory" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-faint">
                <th className="px-4 py-2 font-normal">Cell ID</th>
                <th className="px-4 py-2 font-normal">Site</th>
                <th className="px-4 py-2 font-normal">Band</th>
                <th className="px-4 py-2 font-normal">Scenario</th>
                <th className="px-4 py-2 font-normal">State</th>
                <th className="px-4 py-2 font-normal">Alarms</th>
                <th className="px-4 py-2 font-normal text-right">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {cells.map((c) => (
                <tr key={c.cell_id} className="hover:bg-surface-2">
                  <td className="px-4 py-2.5">
                    <Link href={`/cells/${c.cell_id}`} className="flex items-center gap-2 font-mono text-cyan hover:underline">
                      <StatDot tone={c.health_score >= 80 ? "healthy" : c.health_score >= 50 ? "warning" : "critical"} />
                      {c.cell_id}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-text-dim">{c.site_name}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-text-dim">{c.band}</td>
                  <td className="px-4 py-2.5 text-text-dim">{c.scenario.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2.5"><Badge tone={c.oper_state}>{c.oper_state}</Badge></td>
                  <td className="px-4 py-2.5 text-xs text-text-faint">{c.active_alarms.length ? new Set(c.active_alarms).size : "-"}</td>
                  <td className={`px-4 py-2.5 text-right font-mono ${healthColor(c.health_score)}`}>{c.health_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {topology && (
        <Card>
          <CardHeader title="Network Topology" subtitle="Sites, cells, and neighbor relations" />
          <div className="p-4">
            <TopologyView topology={topology} />
          </div>
        </Card>
      )}
    </div>
  );
}
