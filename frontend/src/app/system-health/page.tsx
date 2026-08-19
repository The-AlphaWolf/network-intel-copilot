"use client";

import { useEffect, useState } from "react";
import { getSystemHealth, SystemHealth } from "@/lib/api";
import { Card, CardHeader, Badge, StatDot, EmptyState } from "@/components/ui";

export default function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () => getSystemHealth().then(setHealth).catch((e) => setError(e.message));
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  if (error) return <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">Backend unreachable: {error}</div>;
  if (!health) return <EmptyState message="Loading..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text">System Health</h1>
          <p className="text-sm text-text-dim">Per-component status of the backend stack.</p>
        </div>
        <Badge tone={health.status === "healthy" ? "healthy" : "warning"}>{health.status}</Badge>
      </div>

      <Card>
        <CardHeader title="Components" />
        <div className="divide-y divide-border">
          {health.components.map((c) => (
            <div key={c.name} className="flex items-center justify-between px-4 py-3 text-sm">
              <div className="flex items-center gap-2">
                <StatDot tone={c.status === "healthy" || c.status === "stub_mode" ? "healthy" : c.status === "not_installed" ? "warning" : "critical"} />
                <span className="text-text capitalize">{c.name.replace(/_/g, " ")}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-faint">{c.detail}</span>
                <Badge tone={c.status === "healthy" || c.status === "stub_mode" ? "healthy" : c.status === "not_installed" ? "warning" : "critical"}>{c.status}</Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <p className="text-xs text-text-faint">Python {health.python_version} · env: {health.app_env}</p>
      </Card>
    </div>
  );
}
