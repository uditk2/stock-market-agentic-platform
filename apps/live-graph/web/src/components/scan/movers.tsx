"use client";

import { ChevronRight } from "lucide-react";

import { Empty } from "@/components/empty";
import { VerdictDot } from "@/components/scan/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Mover, MoversPayload } from "@/lib/api";
import { moveClass, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

export const PER_SIDE_OPTIONS = [10, 20, 30, 50, 100];

const LEGEND: { key: Mover["verdict"]; label: string }[] = [
  { key: "unexplained", label: "unexplained" },
  { key: "conflicted", label: "conflicted" },
  { key: "stock_specific", label: "stock-specific" },
  { key: "sector_wide", label: "sector-wide" },
];

export function Movers({
  data,
  perSide,
  onPerSideChange,
  onPick,
  onPickSector,
}: {
  data: MoversPayload | null;
  perSide: number;
  onPerSideChange: (n: number) => void;
  onPick: (symbol: string) => void;
  onPickSector: (sector: string) => void;
}) {
  if (!data) return <Empty title="Waiting for prices" hint="Rows appear as ticks arrive." />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <p className="text-muted-foreground max-w-xl text-sm">
          The largest moves each way in the F&amp;O tier. The dot says what the move looks
          like before you open it, so a sector moving as a bloc reads as one story.
        </p>
        <div className="space-y-1">
          <Label className="text-xs">Per side</Label>
          <Select value={String(perSide)} onValueChange={(v) => onPerSideChange(Number(v))}>
            <SelectTrigger size="sm" className="w-[110px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PER_SIDE_OPTIONS.map((n) => (
                <SelectItem key={n} value={String(n)}>
                  Top {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {data.sectors.map((s) => (
          <button
            key={s.sector}
            onClick={() => onPickSector(s.sector)}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs transition",
              s.avg_change_pct > 0
                ? "bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-400"
                : "bg-rose-500/10 text-rose-700 hover:bg-rose-500/20 dark:text-rose-400",
            )}
          >
            <span className="font-medium">{s.sector}</span>{" "}
            <span className="tabular-nums">{pct(s.avg_change_pct)}</span>{" "}
            <span className="opacity-70 tabular-nums">
              {s.advancing}↑ {s.declining}↓
            </span>
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Ledger title="Gainers" rows={data.gainers} onPick={onPick} />
        <Ledger title="Losers" rows={data.losers} onPick={onPick} />
      </div>

      <div className="text-muted-foreground flex flex-wrap gap-4 border-t pt-3 text-xs">
        {LEGEND.map(({ key, label }) => (
          <span key={key} className="flex items-center gap-1.5">
            <VerdictDot verdict={key} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

function Ledger({
  title,
  rows,
  onPick,
}: {
  title: string;
  rows: Mover[];
  onPick: (symbol: string) => void;
}) {
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardHeader className="bg-muted/40 border-b py-3">
        <div className="flex items-baseline gap-2">
          <CardTitle className="text-sm">{title}</CardTitle>
          <span className="text-muted-foreground ml-auto text-xs tabular-nums">
            {rows.length} names
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {!rows.length ? (
          <Empty title="Nothing here yet" />
        ) : (
          rows.map((row) => (
            <button
              key={row.symbol}
              onClick={() => onPick(row.symbol)}
              className="hover:bg-accent flex w-full items-center gap-3 border-b px-4 py-2.5 text-left last:border-b-0"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{row.symbol}</span>
                <span className="text-muted-foreground block truncate text-xs">
                  {row.sector ?? "—"}
                </span>
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex shrink-0 items-center">
                    <VerdictDot verdict={row.verdict} />
                  </span>
                </TooltipTrigger>
                <TooltipContent>{row.verdict_label}</TooltipContent>
              </Tooltip>
              <span className={cn("w-16 text-right text-sm tabular-nums", moveClass(row.change_pct))}>
                {pct(row.change_pct)}
              </span>
              <ChevronRight className="text-muted-foreground size-3.5 shrink-0" />
            </button>
          ))
        )}
      </CardContent>
    </Card>
  );
}
