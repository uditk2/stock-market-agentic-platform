"use client";

import { useState } from "react";
import { ExternalLink, Loader2, Newspaper, RefreshCw } from "lucide-react";

import { Empty } from "@/components/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { usePoll } from "@/hooks/use-poll";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";

const POLL_MS = 30000;

export function NewsFeed({ onSelect }: { onSelect: (symbol: string) => void }) {
  const [foOnly, setFoOnly] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { data, refresh } = usePoll(() => api.news(60, foOnly), POLL_MS, [foOnly]);
  const items = data ?? [];

  const pull = async () => {
    setRefreshing(true);
    try {
      await api.refreshNews();
      // Feeds are fetched in the background, so give them a moment before reloading.
      setTimeout(refresh, 4000);
    } finally {
      setTimeout(() => setRefreshing(false), 4000);
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle>News</CardTitle>
          <CardDescription>
            Headlines resolved to graph nodes. Untagged stories are hidden behind the filter.
          </CardDescription>
        </div>
        <div className="flex gap-2">
          <Button variant={foOnly ? "default" : "outline"} size="sm" onClick={() => setFoOnly((v) => !v)}>
            F&O only
          </Button>
          <Button variant="outline" size="sm" onClick={pull} disabled={refreshing}>
            {refreshing ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
            Poll feeds
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {!items.length ? (
          <Empty
            title="No headlines yet"
            hint="Press Poll feeds to fetch the eight configured RSS sources."
            icon={<Newspaper className="size-6" />}
          />
        ) : (
          <div className="divide-border divide-y">
            {items.map((item) => (
              <article key={item.link} className="py-3">
                <div className="flex items-start justify-between gap-3">
                  <a
                    href={item.link}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="group flex-1 text-sm font-medium leading-snug hover:underline"
                  >
                    {item.title}
                    <ExternalLink className="text-muted-foreground ml-1 inline size-3 opacity-0 transition group-hover:opacity-100" />
                  </a>
                  <span className="text-muted-foreground shrink-0 text-xs">{ago(item.ts)}</span>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" className="text-[10px]">{item.source}</Badge>
                  {Object.keys(item.entities).map((nodeId) => (
                    <Badge
                      key={nodeId}
                      variant="outline"
                      className="cursor-pointer text-[10px] hover:bg-accent"
                      onClick={() => onSelect(nodeId)}
                    >
                      {nodeId}
                    </Badge>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
