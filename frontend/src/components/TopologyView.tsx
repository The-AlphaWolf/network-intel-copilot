"use client";

import { Topology } from "@/lib/api";

const W = 900;
const H = 420;
const PAD = 60;

export function TopologyView({ topology }: { topology: Topology }) {
  const sites = Object.entries(topology.sites);
  const lats = sites.map(([, s]) => s.lat);
  const lons = sites.map(([, s]) => s.lon);
  const latRange = [Math.min(...lats), Math.max(...lats)] as const;
  const lonRange = [Math.min(...lons), Math.max(...lons)] as const;

  const project = (lat: number, lon: number) => {
    const x = PAD + ((lon - lonRange[0]) / (lonRange[1] - lonRange[0] || 1)) * (W - 2 * PAD);
    const y = PAD + (1 - (lat - latRange[0]) / (latRange[1] - latRange[0] || 1)) * (H - 2 * PAD);
    return { x, y };
  };

  const sitePositions = new Map(sites.map(([id, s]) => [id, project(s.lat, s.lon)]));
  const cellPositions = new Map<string, { x: number; y: number }>();
  const bySite = new Map<string, typeof topology.cells>();
  for (const c of topology.cells) {
    if (!bySite.has(c.site_id)) bySite.set(c.site_id, []);
    bySite.get(c.site_id)!.push(c);
  }
  for (const [siteId, siteCells] of bySite) {
    const center = sitePositions.get(siteId);
    if (!center) continue;
    const n = siteCells.length;
    siteCells.forEach((c, i) => {
      const angle = (i / n) * 2 * Math.PI;
      cellPositions.set(c.cell_id, { x: center.x + Math.cos(angle) * 55, y: center.y + Math.sin(angle) * 55 });
    });
  }

  const cellById = new Map(topology.cells.map((c) => [c.cell_id, c]));
  const healthDotColor = (score: number) => (score >= 80 ? "#34d399" : score >= 50 ? "#fbbf24" : "#f87171");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minHeight: 360 }}>
      {topology.neighbor_relations.map((rel, i) => {
        const a = cellPositions.get(rel.cell_id);
        const b = cellPositions.get(rel.neighbor_id);
        if (!a || !b) return null;
        const missing = rel.relation_status === "missing";
        return (
          <line
            key={i}
            x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke={missing ? "#f87171" : "#1e293b"}
            strokeWidth={missing ? 1.5 : 1}
            strokeDasharray={missing ? "4 3" : undefined}
          />
        );
      })}

      {sites.map(([id, s]) => {
        const p = sitePositions.get(id)!;
        return (
          <g key={id}>
            <circle cx={p.x} cy={p.y} r={80} fill="none" stroke="#1e293b" strokeDasharray="2 4" />
            <text x={p.x} y={p.y - 90} textAnchor="middle" fontSize={12} fill="#8b98ac">{s.name}</text>
          </g>
        );
      })}

      {topology.cells.map((c) => {
        const p = cellPositions.get(c.cell_id);
        if (!p) return null;
        return (
          <g key={c.cell_id}>
            <circle cx={p.x} cy={p.y} r={7} fill="#0f1626" stroke={healthDotColor(c.health_score)} strokeWidth={2} />
            <text x={p.x} y={p.y + 20} textAnchor="middle" fontSize={9} fill="#5b6b83" fontFamily="monospace">
              {c.cell_id.split("-").pop()}
            </text>
          </g>
        );
      })}

      <g transform={`translate(${W - 170}, ${H - 60})`}>
        <circle cx={0} cy={0} r={5} fill="#0f1626" stroke="#34d399" strokeWidth={2} />
        <text x={12} y={4} fontSize={10} fill="#8b98ac">Healthy</text>
        <circle cx={0} cy={16} r={5} fill="#0f1626" stroke="#fbbf24" strokeWidth={2} />
        <text x={12} y={20} fontSize={10} fill="#8b98ac">Degraded</text>
        <circle cx={0} cy={32} r={5} fill="#0f1626" stroke="#f87171" strokeWidth={2} />
        <text x={12} y={36} fontSize={10} fill="#8b98ac">Critical</text>
      </g>

      {Array.from(cellById.values()).length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fill="#5b6b83" fontSize={12}>No topology data</text>
      )}
    </svg>
  );
}
