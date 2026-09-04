"use client";

import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import type { VerdictKey } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Verdict styling in one place, so the dot and the chip can never disagree. */
const VERDICT_STYLE: Record<VerdictKey, { chip: string; dot: string }> = {
  unexplained: {
    chip: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
    dot: "bg-amber-500",
  },
  conflicted: {
    chip: "border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400",
    dot: "bg-rose-500",
  },
  stock_specific: {
    chip: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-400",
    dot: "bg-sky-500",
  },
  sector_wide: {
    chip: "border-muted-foreground/25 text-muted-foreground",
    dot: "bg-muted-foreground/40",
  },
};

export function VerdictChip({ verdict, label }: { verdict: VerdictKey; label: string }) {
  return (
    <Badge variant="outline" className={cn("font-medium", VERDICT_STYLE[verdict].chip)}>
      {label}
    </Badge>
  );
}

export function VerdictDot({ verdict, className }: { verdict: VerdictKey; className?: string }) {
  return (
    <span className={cn("size-2 shrink-0 rounded-full", VERDICT_STYLE[verdict].dot, className)} />
  );
}

/**
 * A zero-centred bar. Everything on a stock page is measured against zero, so
 * the axis is drawn rather than implied.
 */
export function SignedBar({
  label,
  value,
  span,
}: {
  label: string;
  value: number;
  span: number;
}) {
  const width = (Math.abs(value) / span) * 50;
  const positive = value >= 0;
  return (
    <div className="flex items-center gap-3 py-1 text-xs">
      <span className="text-muted-foreground w-24 shrink-0">{label}</span>
      <span className="bg-muted relative h-1.5 flex-1 rounded-full">
        <span className="bg-border absolute -top-1 bottom-[-4px] left-1/2 w-px" />
        <span
          className={cn(
            "absolute inset-y-0 rounded-full",
            positive ? "bg-emerald-600 dark:bg-emerald-500" : "bg-rose-600 dark:bg-rose-500",
          )}
          style={{ left: positive ? "50%" : `${50 - width}%`, width: `${width}%` }}
        />
      </span>
      <span
        className={cn(
          "w-16 shrink-0 text-right tabular-nums",
          positive ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400",
        )}
      >
        {value > 0 ? "+" : ""}
        {value.toFixed(2)}%
      </span>
    </div>
  );
}

export function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-muted-foreground flex items-baseline gap-2 text-xs font-medium tracking-wide uppercase">
        {title}
        {hint && <span className="normal-case tracking-normal opacity-80">{hint}</span>}
      </h3>
      {children}
    </section>
  );
}
