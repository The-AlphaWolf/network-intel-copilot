import clsx from "clsx";
import { severityColor } from "@/lib/format";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={clsx("rounded-lg border border-border bg-surface", className)}>{children}</div>
  );
}

export function CardHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-3">
      <div>
        <h3 className="text-sm font-medium text-text">{title}</h3>
        {subtitle && <p className="text-xs text-text-faint mt-0.5">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Badge({ children, tone }: { children: React.ReactNode; tone?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        severityColor(tone || "default")
      )}
    >
      {children}
    </span>
  );
}

export function StatDot({ tone }: { tone: "healthy" | "warning" | "critical" | "idle" }) {
  const color = { healthy: "bg-emerald", warning: "bg-amber", critical: "bg-red", idle: "bg-text-faint" }[tone];
  return <span className={clsx("inline-block h-2 w-2 rounded-full", color)} />;
}

export function KpiTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-xs text-text-dim">{label}</p>
      <p className="mt-1 font-mono text-2xl font-semibold text-text">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-text-faint">{sub}</p>}
    </Card>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="px-4 py-8 text-center text-sm text-text-faint">{message}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-3 text-sm text-red">
      {message}
    </div>
  );
}
