"use client";

import { useState } from "react";
import { GitBranch, Loader2, Sparkles } from "lucide-react";

import { Empty } from "@/components/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { usePoll } from "@/hooks/use-poll";
import { api } from "@/lib/api";

const POLL_MS = 15000;

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "border-emerald-500/40 text-emerald-700 dark:text-emerald-400",
  moderate: "border-amber-500/40 text-amber-700 dark:text-amber-400",
  low: "border-muted-foreground/30 text-muted-foreground",
};

export function EdgeProposals({ onSelect }: { onSelect: (symbol: string) => void }) {
  const [review, setReview] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const { data } = usePoll(() => api.edgeProposals(20), POLL_MS);
  const rows = data ?? [];

  const runReview = async () => {
    setReviewing(true);
    setReview(null);
    try {
      setReview((await api.reviewEdgeProposals()).text);
    } catch (error) {
      setReview(error instanceof Error ? error.message : String(error));
    } finally {
      setReviewing(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
          <div>
            <CardTitle>Proposed edges</CardTitle>
            <CardDescription>
              Pairs moving together that the graph does not connect. Correlation is
              not a relationship, so these are candidates for you to accept or reject.
            </CardDescription>
          </div>
          <Button onClick={runReview} disabled={reviewing || !rows.length} size="sm">
            {reviewing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            Ask the analyst
          </Button>
        </CardHeader>
        <CardContent>
          {!rows.length ? (
            <Empty
              title="Not enough history yet"
              hint="A pair needs at least 30 sampled observations before its correlation is reported. Samples are taken every 5 seconds."
              icon={<GitBranch className="size-6" />}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pair</TableHead>
                  <TableHead className="text-right">Correlation</TableHead>
                  <TableHead className="text-right">Samples</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Caveat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={`${row.source}-${row.target}`}>
                    <TableCell className="font-medium">
                      <button className="hover:underline" onClick={() => onSelect(row.source)}>
                        {row.source}
                      </button>
                      <span className="text-muted-foreground mx-1.5">↔</span>
                      <button className="hover:underline" onClick={() => onSelect(row.target)}>
                        {row.target}
                      </button>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.correlation.toFixed(3)}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-right tabular-nums">
                      {row.samples}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={CONFIDENCE_STYLES[row.confidence]}>
                        {row.confidence}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {row.same_sector ? "Same sector; shared index flow is likelier" : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {review && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analyst review</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{review}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
