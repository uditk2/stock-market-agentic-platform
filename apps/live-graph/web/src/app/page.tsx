"use client";

import { useState } from "react";
import { GitBranch, MessageSquare, Network, Newspaper, Radar, Settings, Terminal } from "lucide-react";

import { FeedBadge } from "@/components/feed-badge";
import { Analyst } from "@/components/panels/analyst";
import { EdgeProposals } from "@/components/panels/edge-proposals";
import { GraphView } from "@/components/panels/graph-view";
import { Admin } from "@/components/panels/admin";
import { NewsFeed } from "@/components/panels/news-feed";
import { Scan } from "@/components/scan";
import { Scratchpad } from "@/components/panels/scratchpad";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePoll } from "@/hooks/use-poll";
import { useTicks } from "@/hooks/use-ticks";
import { api } from "@/lib/api";

const STATUS_POLL_MS = 5000;

const TABS = [
  { value: "scan", label: "Scan", icon: Radar },
  { value: "graph", label: "Graph", icon: Network },
  { value: "scratchpad", label: "Scratchpad", icon: Terminal },
  { value: "analyst", label: "Analyst", icon: MessageSquare },
  { value: "edges", label: "Proposed edges", icon: GitBranch },
  { value: "news", label: "News", icon: Newspaper },
  { value: "admin", label: "Admin", icon: Settings },
];

export default function Home() {
  const { ticks, connected } = useTicks();
  const { data: status } = usePoll(() => api.status(), STATUS_POLL_MS);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState("scan");
  const [perSide, setPerSide] = useState(10);

  /** Selecting from a panel focuses the graph on that node. */
  const select = (symbol: string) => {
    setSelected(symbol);
    if (tab === "news") setTab("graph");
  };

  return (
    <div className="bg-background min-h-screen">
      <header className="bg-background/80 sticky top-0 z-30 border-b backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
          <div className="flex items-center gap-2">
            <Network className="size-5" />
            <h1 className="text-base font-semibold tracking-tight">livegraph</h1>
            <span className="text-muted-foreground hidden text-xs sm:inline">
              NSE F&amp;O prices on a sector relationship graph
            </span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {selected && (
              <Badge
                variant="outline"
                className="cursor-pointer gap-1.5"
                onClick={() => setSelected(null)}
              >
                {selected}
                <span className="text-muted-foreground">×</span>
              </Badge>
            )}
            <FeedBadge status={status} socketConnected={connected} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-5 py-5">
        <Tabs value={tab} onValueChange={setTab} className="space-y-4">
          <TabsList className="flex-wrap">
            {TABS.map(({ value, label, icon: Icon }) => (
              <TabsTrigger key={value} value={value} className="gap-1.5">
                <Icon className="size-3.5" />
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="scan">
            <Scan perSide={perSide} onPerSideChange={setPerSide} />
          </TabsContent>
          <TabsContent value="graph">
            <GraphView ticks={ticks} selected={selected} onSelect={setSelected} />
          </TabsContent>
          <TabsContent value="scratchpad">
            <Scratchpad />
          </TabsContent>
          <TabsContent value="analyst">
            <Analyst selected={selected} />
          </TabsContent>
          <TabsContent value="edges">
            <EdgeProposals onSelect={select} />
          </TabsContent>
          <TabsContent value="news">
            <NewsFeed onSelect={select} />
          </TabsContent>
          <TabsContent value="admin">
            <Admin />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
