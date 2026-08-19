export function severityColor(sev: string): string {
  switch (sev) {
    case "critical":
      return "text-red bg-red/10 border-red/30";
    case "warning":
      return "text-amber bg-amber/10 border-amber/30";
    case "healthy":
    case "normal":
    case "completed":
    case "active":
    case "up":
      return "text-emerald bg-emerald/10 border-emerald/30";
    default:
      return "text-text-dim bg-surface-2 border-border";
  }
}

export function healthColor(score: number): string {
  if (score >= 80) return "text-emerald";
  if (score >= 50) return "text-amber";
  return "text-red";
}

export function formatKpiName(kpi: string): string {
  return kpi
    .replace(/_pct$/, " %")
    .replace(/_dbm$/, " (dBm)")
    .replace(/_db$/, " (dB)")
    .replace(/_ms$/, " (ms)")
    .replace(/_mbps$/, " (Mbps)")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
