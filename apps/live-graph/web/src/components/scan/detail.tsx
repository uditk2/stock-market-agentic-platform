"use client";

import { Empty } from "@/components/empty";
import { VerdictDot } from "@/components/scan/shared";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { SectorDetail, StockScan } from "@/lib/api";
import { moveClass, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

export function PeersView({ scan }: { scan: StockScan }) {
  const { evidence } = scan;
  if (!scan.peers.length) {
    return (
      <Empty
        title="No priced peers"
        hint={`Nothing in ${scan.symbol}'s peer group has a live price, so the verdict fell back to sector breadth.`}
      />
    );
  }

  const rows = [
    { symbol: scan.symbol, change_pct: scan.change_pct, vs_peer_avg: evidence.gap ?? 0, me: true },
    ...scan.peers.map((p) => ({ ...p, me: false })),
  ].sort((a, b) => b.change_pct - a.change_pct);

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-xl text-sm">
        Every priced name sharing this peer group. The gap between {scan.symbol} and this
        average is what the verdict turns on.
      </p>
      <Card>
        <CardContent className="pt-5">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead className="text-right">Move</TableHead>
                <TableHead className="text-right">vs peer avg</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.symbol} className={cn(row.me && "bg-accent/60")}>
                  <TableCell className="font-medium">
                    {row.symbol}
                    {row.me && <span className="text-muted-foreground ml-2 text-xs">this stock</span>}
                  </TableCell>
                  <TableCell className={cn("text-right tabular-nums", moveClass(row.change_pct))}>
                    {pct(row.change_pct)}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-right tabular-nums">
                    {row.vs_peer_avg > 0 ? "+" : ""}
                    {row.vs_peer_avg.toFixed(2)}pp
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="text-muted-foreground mt-3 border-t pt-3 text-xs">
            Peer average {pct(evidence.peer_avg)} over {evidence.peer_count} priced names.
            Unpriced peers are left out rather than counted as zero.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export function SectorView({
  detail,
  focus,
  onPick,
}: {
  detail: SectorDetail | null;
  focus: string;
  onPick: (symbol: string) => void;
}) {
  if (!detail) return <Empty title="Loading sector…" />;
  const { sector, members } = detail;
  const breadth = Math.max(1, sector.breadth);

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-xl text-sm">
        {sector.advancing} of {sector.breadth} priced members are advancing.
        {sector.one_sided
          ? " With breadth this one-sided, a move in any single member is usually the sector, not the name."
          : " Breadth is mixed, so a move here is more likely to be the stock's own."}
      </p>
      <Card>
        <CardContent className="space-y-1 pt-5">
          <Bar label="Advancing" count={sector.advancing} total={breadth} tone="up" />
          <Bar label="Declining" count={sector.declining} total={breadth} tone="down" />
          <div className="flex items-center gap-3 pt-1 text-xs">
            <span className="text-muted-foreground w-24">Average</span>
            <span className="flex-1" />
            <span className={cn("w-16 text-right tabular-nums", moveClass(sector.avg_change_pct))}>
              {pct(sector.avg_change_pct)}
            </span>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-5">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead className="text-right">Move</TableHead>
                <TableHead className="text-right">Verdict</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((m) => (
                <TableRow
                  key={m.symbol}
                  onClick={() => onPick(m.symbol)}
                  className={cn("cursor-pointer", m.symbol === focus && "bg-accent/60")}
                >
                  <TableCell className="font-medium">{m.symbol}</TableCell>
                  <TableCell className={cn("text-right tabular-nums", moveClass(m.change_pct))}>
                    {pct(m.change_pct)}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="inline-flex items-center gap-1.5 text-xs">
                      <VerdictDot verdict={m.verdict} />
                      <span className="text-muted-foreground">{m.verdict_label}</span>
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function Bar({
  label,
  count,
  total,
  tone,
}: {
  label: string;
  count: number;
  total: number;
  tone: "up" | "down";
}) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="text-muted-foreground w-24">{label}</span>
      <span className="bg-muted relative h-1.5 flex-1 rounded-full">
        <span
          className={cn(
            "absolute inset-y-0 left-0 rounded-full",
            tone === "up" ? "bg-emerald-600 dark:bg-emerald-500" : "bg-rose-600 dark:bg-rose-500",
          )}
          style={{ width: `${(count / total) * 100}%` }}
        />
      </span>
      <span className="w-16 text-right tabular-nums">{count}</span>
    </div>
  );
}

export function DriversView({ scan }: { scan: StockScan }) {
  if (!scan.drivers.length) {
    return <Empty title="No graph drivers" hint={`${scan.symbol} has no non-peer edges.`} />;
  }
  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-xl text-sm">
        Typed edges from the relationship graph. The sign says how the driver&apos;s move
        translates: a negative cost input rising pushes the stock down.
      </p>
      <Card>
        <CardContent className="divide-y pt-5">
          {scan.drivers.map((d, index) => (
            <div key={`${d.node}-${index}`} className="flex flex-wrap items-center gap-3 py-2.5 first:pt-0">
              <Badge variant="outline" className="font-mono text-[10px]">
                {d.edge_type}
              </Badge>
              <span className="text-sm font-medium">{d.node}</span>
              <span
                className={cn(
                  "text-xs tabular-nums",
                  d.sign > 0 ? "text-emerald-600 dark:text-emerald-400" : d.sign < 0 ? "text-rose-600 dark:text-rose-400" : "text-muted-foreground",
                )}
              >
                sign {d.sign > 0 ? "+1" : d.sign < 0 ? "−1" : "0"}
              </span>
              <span className={cn("text-xs tabular-nums", moveClass(d.driver_change_pct))}>
                {d.driver_change_pct === null ? "not priced" : pct(d.driver_change_pct)}
              </span>
              {d.conflicting && (
                <Badge variant="outline" className="border-rose-500/40 text-rose-700 dark:text-rose-400">
                  disagrees with the price
                </Badge>
              )}
              <span className="text-muted-foreground ml-auto max-w-[45%] text-right text-xs">
                {d.note ?? ""}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
      <p className="text-muted-foreground text-xs">
        Direction is the reliable output. Edge strength ranks impacts against each other and
        is not a forecast.
      </p>
    </div>
  );
}
