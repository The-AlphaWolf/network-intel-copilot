"use client";

import { useEffect, useState } from "react";
import { getSystemHealth } from "@/lib/api";
import { StatDot } from "@/components/ui";

export function Topbar() {
  const [status, setStatus] = useState<"healthy" | "warning" | "critical" | "idle">("idle");
  const [now, setNow] = useState<string>("");

  useEffect(() => {
    const tick = () => setNow(new Date().toLocaleTimeString());
    tick();
    const clock = setInterval(tick, 1000);

    const checkHealth = () =>
      getSystemHealth()
        .then((h) => setStatus(h.status === "healthy" ? "healthy" : "warning"))
        .catch(() => setStatus("critical"));
    checkHealth();
    const health = setInterval(checkHealth, 15000);

    return () => {
      clearInterval(clock);
      clearInterval(health);
    };
  }, []);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <div className="flex items-center gap-2">
        <span className="rounded border border-border bg-surface-2 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-text-dim">
          Development
        </span>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5">
          <StatDot tone={status} />
          <span className="text-text-dim">
            {status === "healthy" ? "Backend Online" : status === "critical" ? "Backend Unreachable" : "Checking..."}
          </span>
        </div>
        <span className="font-mono text-text-faint">{now}</span>
      </div>
    </header>
  );
}
