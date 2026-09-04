"use client";

import { ChevronRight, Globe, Loader2, Sparkles } from "lucide-react";

import { Empty } from "@/components/empty";
import { Section, SignedBar, VerdictChip } from "@/components/scan/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { ScopedNews, StockScan } from "@/lib/api";
import { ago, moveClass, pct, price } from "@/lib/format";
import { cn } from "@/lib/utils";

const SCOPE_STYLE: Record<ScopedNews["scope"], string> = {
  stock: "border-sky-500/40 text-sky-700 dark:text-sky-400",
  sector: "border-muted-foreground/30 text-muted-foreground",
  market: "border-muted-foreground/20 text-muted-foreground",
  web: "border-amber-500/40 text-amber-700 dark:text-amber-400",
};

export function StockView({
  scan,
  searching,
  onSearchWeb,
  onDrill,
}: {
  scan: StockScan;
  searching: boolean;
  onSearchWeb: () => void;
  onDrill: (view: "peers" | "sector" | "drivers") => void;
}) {
  const { evidence, sector_context: sector } = scan;
  const span = Math.max(
    1,
    Math.abs(scan.change_pct),
    Math.abs(evidence.peer_avg ?? 0),
    Math.abs(sector?.avg_change_pct ?? 0),
  );
  const hasStockNews = scan.news.some((n) => n.scope === "stock" || n.scope === "web");

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">{scan.symbol}</h2>
            <span className={cn("text-2xl tabular-nums", moveClass(scan.change_pct))}>
              {pct(scan.change_pct)}
            </span>
            <span className="text-muted-foreground tabular-nums">{price(scan.ltp)}</span>
            <span className="ml-auto">
              <VerdictChip verdict={scan.verdict} label={scan.verdict_label} />
            </span>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">{scan.name}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {scan.sector && <Badge variant="secondary">{scan.sector}</Badge>}
            {scan.peer_groups.map((g) => (
              <Badge key={g} variant="outline" className="font-mono text-[10px]">
                {g}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Section title="The move" hint="how it sits against everything around it">
        <Card>
          <CardContent className="pt-5">
            <SignedBar label="This stock" value={scan.change_pct} span={span} />
            {evidence.peer_avg !== null && (
              <SignedBar label="Peer group" value={evidence.peer_avg} span={span} />
            )}
            {sector && <SignedBar label="Sector" value={sector.avg_change_pct} span={span} />}
          </CardContent>
        </Card>

        <DrillRow
          title={`Peer group${scan.peer_groups.length ? ` · ${scan.peer_groups[0]}` : ""}`}
          value={evidence.gap === null ? "—" : `${evidence.gap > 0 ? "+" : ""}${evidence.gap.toFixed(2)}pp gap`}
          valueClass={moveClass(evidence.gap)}
          detail={
            evidence.peer_avg === null
              ? `Only ${evidence.peer_count} priced peers, too few to compare against.`
              : `${evidence.peer_count} priced names averaging ${pct(evidence.peer_avg)}. See each one.`
          }
          onClick={() => onDrill("peers")}
        />
        {sector && (
          <DrillRow
            title={`Sector · ${sector.name}`}
            value={pct(sector.avg_change_pct)}
            valueClass={moveClass(sector.avg_change_pct)}
            detail={`${sector.advancing} advancing, ${sector.declining} declining. See the breadth.`}
            onClick={() => onDrill("sector")}
          />
        )}
      </Section>

      <Section title="What is behind it">
        <Card>
          <CardContent className="pt-5">
            {!scan.news.length ? (
              <p className="text-muted-foreground text-sm">
                Nothing tagged to {scan.symbol}, its sector, or the market.
              </p>
            ) : (
              <div className="divide-y">
                {scan.news.map((item, index) => (
                  <NewsRow key={`${item.link}-${index}`} item={item} />
                ))}
              </div>
            )}
            {!hasStockNews && (
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={onSearchWeb}
                disabled={searching}
              >
                {searching ? <Loader2 className="size-4 animate-spin" /> : <Globe className="size-4" />}
                Search the web for {scan.symbol}
              </Button>
            )}
          </CardContent>
        </Card>
        <DrillRow
          title="Graph drivers"
          value={`${scan.drivers.length} edges`}
          detail="What the relationship graph says should move this name."
          onClick={() => onDrill("drivers")}
        />
      </Section>

      <Section title={`Verdict · ${scan.verdict_label}`}>
        <Card>
          <CardContent className="space-y-3 pt-5">
            <p className="text-sm leading-relaxed">{scan.why}</p>
            {scan.narration ? (
              <div className="border-t pt-3">
                <div className="text-muted-foreground mb-1.5 flex items-center gap-1.5 text-xs">
                  <Sparkles className="size-3" />
                  Analyst
                  <span className="opacity-70">
                    · written {ago(scan.narration.written_at)}
                    {scan.narration.from_cache
                      ? ", unchanged since"
                      : ` · ${scan.narration.refreshed_because}`}
                  </span>
                </div>
                <p className="text-sm leading-relaxed">{scan.narration.text}</p>
              </div>
            ) : (
              <p className="text-muted-foreground border-t pt-3 text-xs">
                No analyst note. The verdict above is computed and stands on its own.
              </p>
            )}
          </CardContent>
        </Card>
        <p className="text-muted-foreground text-xs">
          Evidence: peer average over {evidence.peer_count} names
          {sector && `, sector breadth ${sector.advancing}↑/${sector.declining}↓`}
          {`, ${scan.news.length || "no"} headline${scan.news.length === 1 ? "" : "s"}`}
          {`, ${scan.drivers.length} graph edge${scan.drivers.length === 1 ? "" : "s"}.`}
        </p>
      </Section>
    </div>
  );
}

function NewsRow({ item }: { item: ScopedNews }) {
  return (
    <div className="flex gap-3 py-2.5 first:pt-0 last:pb-0">
      <Badge
        variant="outline"
        className={cn("h-fit w-16 shrink-0 justify-center font-mono text-[10px]", SCOPE_STYLE[item.scope])}
      >
        {item.scope}
      </Badge>
      <div className="min-w-0">
        {item.link ? (
          <a
            href={item.link}
            target="_blank"
            rel="noreferrer noopener"
            className="text-sm leading-snug hover:underline"
          >
            {item.title}
          </a>
        ) : (
          <span className="text-sm leading-snug">{item.title}</span>
        )}
        <span className="text-muted-foreground block text-xs">
          {item.source}
          {item.matched_node && item.scope !== "stock" && ` · tagged ${item.matched_node}`}
        </span>
      </div>
    </div>
  );
}

function DrillRow({
  title,
  value,
  valueClass,
  detail,
  onClick,
}: {
  title: string;
  value: string;
  valueClass?: string;
  detail: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="hover:border-primary/50 hover:bg-accent/40 bg-card w-full rounded-lg border px-4 py-3 text-left transition"
    >
      <span className="flex items-center gap-3">
        <span className="text-sm font-medium">{title}</span>
        <span className={cn("ml-auto text-sm tabular-nums", valueClass)}>{value}</span>
        <ChevronRight className="text-muted-foreground size-3.5" />
      </span>
      <span className="text-muted-foreground mt-0.5 block text-xs">{detail}</span>
    </button>
  );
}

export function StockLoading() {
  return <Empty title="Loading…" />;
}
