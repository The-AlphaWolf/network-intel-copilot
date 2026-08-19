"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard, Search, Radio, BookOpen, Bot, LineChart, HeartPulse, Signal,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/investigations", label: "Investigations", icon: Search },
  { href: "/cells", label: "Cells", icon: Radio },
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/evaluation", label: "Evaluation", icon: LineChart },
  { href: "/system-health", label: "System Health", icon: HeartPulse },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-cyan to-blue">
          <Signal className="h-4 w-4 text-bg" strokeWidth={2.5} />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight text-text">Network Intelligence</p>
          <p className="text-[11px] leading-tight text-text-faint">Copilot</p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-cyan/10 text-cyan"
                  : "text-text-dim hover:bg-surface-2 hover:text-text"
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={2} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border px-4 py-3 text-[11px] text-text-faint">
        Synthetic telecom data · demo system
      </div>
    </aside>
  );
}
