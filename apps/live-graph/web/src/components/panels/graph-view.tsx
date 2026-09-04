"use client";

/**
 * Force-directed view of the relationship graph, coloured by live move.
 *
 * Nodes are drawn on canvas rather than as DOM, because 200+ nodes and 800+
 * links re-tinted on every tick batch is far too much for React reconciliation.
 */

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Network } from "lucide-react";

import { Empty } from "@/components/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePoll } from "@/hooks/use-poll";
import { api, type GraphEdge, type GraphPayload, type Quote } from "@/lib/api";
import { moveColor, pct } from "@/lib/format";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="text-muted-foreground flex h-[600px] items-center justify-center gap-2 text-sm">
      <Loader2 className="size-4 animate-spin" /> Loading graph…
    </div>
  ),
});

const EDGE_COLORS: Record<string, string> = {
  PEER_OF: "rgba(148,163,184,0.35)",
  COST_INPUT: "rgba(244,63,94,0.45)",
  DEMAND_DRIVER: "rgba(16,185,129,0.45)",
  SUPPLIES: "rgba(59,130,246,0.45)",
  READ_THROUGH: "rgba(168,85,247,0.45)",
  IN_SECTOR: "rgba(148,163,184,0.15)",
};

const EDGE_TYPES = ["ALL", "PEER_OF", "COST_INPUT", "DEMAND_DRIVER", "SUPPLIES", "READ_THROUGH"];

interface Sim { id: string; label: string; type: string; sector: string | null; val: number }

/**
 * react-force-graph hands its callbacks a loose node/link shape, so the extra
 * fields we attach are narrowed at the call site rather than declared on the
 * parameter, which the library's generics reject.
 */
type Positioned = { x?: number; y?: number };
const asSim = (node: unknown) => node as Sim & Positioned;
const asEdge = (link: unknown) => link as GraphEdge;

export function GraphView({
  ticks,
  selected,
  onSelect,
}: {
  ticks: Record<string, Quote>;
  selected: string | null;
  onSelect: (symbol: string) => void;
}) {
  const [edgeType, setEdgeType] = useState("ALL");
  const [scope, setScope] = useState<"fo" | "focus">("fo");
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<{ d3Force: (name: string) => { strength?: (v: number) => void; distance?: (v: number) => void } | undefined } | null>(null);
  const [width, setWidth] = useState(900);

  const { data, loading } = usePoll<GraphPayload>(
    () =>
      scope === "focus" && selected
        ? api.neighbourhood(selected, 1)
        : api.graph(true, false),
    0,
    [scope, selected],
  );

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const graph = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const edges = data.edges.filter((e) => edgeType === "ALL" || e.type === edgeType);
    // Drop nodes the filter left unconnected, so the canvas is not a dust cloud
    // of isolated dots when a narrow edge type is selected.
    const connected = new Set(edges.flatMap((e) => [e.source, e.target]));
    const nodes = data.nodes
      .filter((n) => connected.has(n.id) || n.id === selected)
      .map<Sim>((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        sector: n.sector,
        val: n.type === "macro" ? 6 : 3,
      }));
    const present = new Set(nodes.map((n) => n.id));
    return {
      nodes,
      links: edges
        .filter((e) => present.has(e.source) && present.has(e.target))
        .map((e: GraphEdge) => ({ ...e })),
    };
  }, [data, edgeType, selected]);

  // PEER_OF alone contributes ~1900 edges, so the default forces collapse the
  // graph into an unclickable knot. Push nodes apart and lengthen links.
  // Applied once per dataset: re-applying on every tick reheats the simulation
  // and the nodes never settle, so they drift out from under the pointer.
  useEffect(() => {
    const charge = graphRef.current?.d3Force("charge");
    charge?.strength?.(-190);
    const link = graphRef.current?.d3Force("link");
    link?.distance?.(40);
  }, [graph]);

  const paintNode = useCallback(
    (raw: unknown, ctx: CanvasRenderingContext2D, scale: number) => {
      const node = asSim(raw);
      const move = ticks[node.id]?.change_pct ?? null;
      const radius = node.type === "macro" ? 6 : 4;
      const isSelected = node.id === selected;

      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.type === "macro" ? "hsl(217 91% 60%)" : moveColor(move);
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = "hsl(45 93% 47%)";
        ctx.lineWidth = 2 / scale;
        ctx.stroke();
      }

      // Labels only once zoomed in, otherwise they overlap into an unreadable smear.
      if (scale > 2.2 || isSelected || node.type === "macro") {
        ctx.font = `${Math.max(3, 10 / scale)}px ui-sans-serif, system-ui`;
        ctx.fillStyle = "hsl(215 16% 47%)";
        ctx.textAlign = "center";
        ctx.fillText(node.label, node.x ?? 0, (node.y ?? 0) + radius + 8 / scale);
      }
    },
    [ticks, selected],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <Card className="overflow-hidden">
        <CardHeader className="flex-row items-center justify-between gap-4 space-y-0">
          <div>
            <CardTitle>Relationship graph</CardTitle>
            <CardDescription>
              {graph.nodes.length} nodes · {graph.links.length} edges. Node colour is the live move.
            </CardDescription>
          </div>
          <div className="flex items-end gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Scope</Label>
              <Select value={scope} onValueChange={(v) => setScope(v as "fo" | "focus")}>
                <SelectTrigger size="sm" className="w-[150px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fo">All F&O</SelectItem>
                  <SelectItem value="focus" disabled={!selected}>
                    {selected ? `Around ${selected}` : "Around selection"}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Edge type</Label>
              <Select value={edgeType} onValueChange={setEdgeType}>
                <SelectTrigger size="sm" className="w-[160px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EDGE_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type === "ALL" ? "All types" : type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div ref={containerRef} className="h-[600px] w-full">
            {loading ? (
              <div className="text-muted-foreground flex h-full items-center justify-center gap-2 text-sm">
                <Loader2 className="size-4 animate-spin" /> Loading graph…
              </div>
            ) : !graph.nodes.length ? (
              <Empty
                title="No edges of this type"
                hint="Try a different edge type or widen the scope."
                icon={<Network className="size-6" />}
              />
            ) : (
              <ForceGraph2D
                ref={graphRef as never}
                graphData={graph}
                width={width}
                height={600}
                backgroundColor="transparent"
                // Pre-settle off-screen so the layout is stable the moment it
                // appears, instead of drifting under the pointer.
                warmupTicks={120}
                d3VelocityDecay={0.35}
                nodeCanvasObject={paintNode}
                nodePointerAreaPaint={(raw, color, ctx) => {
                  const node = asSim(raw);
                  ctx.fillStyle = color;
                  ctx.beginPath();
                  ctx.arc(node.x ?? 0, node.y ?? 0, 10, 0, 2 * Math.PI);
                  ctx.fill();
                }}
                linkColor={(link) => EDGE_COLORS[asEdge(link).type] ?? "rgba(148,163,184,0.3)"}
                linkWidth={(link) => 0.4 + asEdge(link).strength}
                cooldownTicks={90}
                nodeRelSize={5}
                enableNodeDrag
                onNodeClick={(node) => onSelect(asSim(node).id)}
              />
            )}
          </div>
        </CardContent>
      </Card>

      <NodeDetail symbol={selected} ticks={ticks} onSelect={onSelect} />
    </div>
  );
}

function NodeDetail({
  symbol,
  ticks,
  onSelect,
}: {
  symbol: string | null;
  ticks: Record<string, Quote>;
  onSelect: (symbol: string) => void;
}) {
  const { data } = usePoll(
    () => (symbol ? api.neighbourhood(symbol, 1) : Promise.resolve(null)),
    0,
    [symbol],
  );
  const { data: impact } = usePoll(
    () => (symbol ? api.impact(symbol, "up") : Promise.resolve(null)),
    0,
    [symbol],
  );

  if (!symbol) {
    return (
      <Card>
        <CardContent className="pt-6">
          <Empty
            title="Select a node"
            hint="Click any node in the graph, or a row in a table, to see its connections and what the graph says it drives."
            icon={<Network className="size-6" />}
          />
        </CardContent>
      </Card>
    );
  }

  const node = data?.nodes.find((n) => n.id === symbol);
  const quote = ticks[symbol];
  const links = (data?.edges ?? []).filter(
    (e) => e.source === symbol || e.target === symbol,
  );

  return (
    <Card className="max-h-[660px] overflow-y-auto">
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>{symbol}</span>
          <span className={`tabular-nums text-base ${quote ? "" : "text-muted-foreground"}`}>
            {pct(quote?.change_pct)}
          </span>
        </CardTitle>
        <CardDescription>{node?.name ?? "—"}</CardDescription>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {node?.sector && <Badge variant="secondary">{node.sector}</Badge>}
          {node?.fo && <Badge variant="outline">F&O</Badge>}
          {node?.peer_groups.map((group) => (
            <Badge key={group} variant="outline" className="font-mono text-[10px]">
              {group}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <section>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Connections ({links.length})
          </h4>
          <div className="space-y-1">
            {links.slice(0, 12).map((edge, index) => {
              const other = edge.source === symbol ? edge.target : edge.source;
              return (
                <Button
                  key={`${other}-${index}`}
                  variant="ghost"
                  size="sm"
                  onClick={() => onSelect(other)}
                  className="h-auto w-full justify-between px-2 py-1.5"
                >
                  <span className="flex items-center gap-2">
                    <span
                      className="size-2 rounded-full"
                      style={{ background: EDGE_COLORS[edge.type] ?? "#94a3b8" }}
                    />
                    <span className="font-medium">{other}</span>
                    <span className="text-muted-foreground text-[10px] font-mono">
                      {edge.type}
                      {edge.sign !== 0 && (edge.sign > 0 ? " +" : " −")}
                    </span>
                  </span>
                  <span className={`tabular-nums text-xs ${ticks[other] ? "" : "text-muted-foreground"}`}>
                    {pct(ticks[other]?.change_pct)}
                  </span>
                </Button>
              );
            })}
            {!links.length && (
              <p className="text-muted-foreground text-xs">No non-membership edges.</p>
            )}
          </div>
        </section>

        {impact && impact.length > 0 && (
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              If {symbol} rises
            </h4>
            <p className="text-muted-foreground mb-2 text-[11px] leading-relaxed">
              Direction is the reliable output. Magnitude is a heuristic ranking, not a forecast.
            </p>
            <div className="space-y-1">
              {impact.slice(0, 8).map((row) => (
                <div key={row.symbol} className="flex items-center justify-between px-2 text-xs">
                  <span className="font-medium">{row.symbol}</span>
                  <span className="flex items-center gap-3">
                    <span className={row.expected === "up" ? "text-emerald-600" : "text-rose-600"}>
                      {row.expected === "up" ? "▲" : "▼"} {Math.abs(row.relative_magnitude).toFixed(2)}
                    </span>
                    <span className="text-muted-foreground tabular-nums">
                      {pct(row.actual_change_pct)}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}
