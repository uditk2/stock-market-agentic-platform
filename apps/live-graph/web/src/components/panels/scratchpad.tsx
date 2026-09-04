"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Code2, Loader2, Play, RefreshCw, Send, Terminal } from "lucide-react";

import { Empty } from "@/components/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { usePoll } from "@/hooks/use-poll";
import { api, type ScratchpadTurn } from "@/lib/api";

interface Entry {
  prompt: string;
  turn: ScratchpadTurn | null;
  error?: string;
}

const EXAMPLES = [
  "Rank F&O names by how far they diverge from their peer group average, top 10, and chart the gaps.",
  "Find sectors where more than 70% of priced members move the same way, and show the breadth as a bar chart.",
  "Show the 15 widest spreads between a stock and its sector average, as a table.",
];

export function Scratchpad() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const { data: health } = usePoll(() => api.scratchpadHealth(), 20000);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, busy]);

  const send = async (prompt: string) => {
    if (!prompt.trim() || busy) return;
    setEntries((e) => [...e, { prompt, turn: null }]);
    setInput("");
    setBusy(true);
    try {
      const turn = await api.scratchpadSend(prompt, threadId);
      setThreadId(turn.thread_id);
      setEntries((e) => [...e.slice(0, -1), { prompt, turn }]);
    } catch (error) {
      setEntries((e) => [
        ...e.slice(0, -1),
        { prompt, turn: null, error: error instanceof Error ? error.message : String(error) },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const rerun = async () => {
    if (!threadId || busy) return;
    setBusy(true);
    try {
      const turn = await api.scratchpadRerun(threadId);
      setEntries((e) => [...e, { prompt: "Re-run on a fresh snapshot", turn }]);
    } finally {
      setBusy(false);
    }
  };

  if (health && !health.sandbox_available) {
    return (
      <Card>
        <CardContent className="pt-6">
          <Empty
            title="Strategy sandbox unavailable"
            hint={health.detail}
            icon={<AlertTriangle className="size-6" />}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
          <div>
            <CardTitle>Strategy scratchpad</CardTitle>
            <CardDescription>
              Describe a strategy in plain English. It is written for you, then run
              against a live snapshot inside an offline container.
            </CardDescription>
          </div>
          {threadId && (
            <Button variant="outline" size="sm" onClick={rerun} disabled={busy}>
              <RefreshCw className="size-4" />
              Re-run on fresh data
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault();
                  send(input);
                }
              }}
              placeholder="e.g. rank F&O names by divergence from their peer group and chart the top 10…"
              className="min-h-[80px] resize-none"
            />
            <Button onClick={() => send(input)} disabled={busy || !input.trim()} className="h-auto shrink-0">
              {busy ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            </Button>
          </div>
          {!entries.length && (
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <Button
                  key={example}
                  variant="outline"
                  size="sm"
                  className="h-auto whitespace-normal py-1.5 text-left text-xs"
                  onClick={() => send(example)}
                >
                  {example}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {entries.map((entry, index) => (
        <ResultCard key={index} entry={entry} />
      ))}
      {busy && (
        <Card>
          <CardContent className="text-muted-foreground flex items-center gap-2 py-6 text-sm">
            <Loader2 className="size-4 animate-spin" />
            Writing the strategy, then running it in the sandbox…
          </CardContent>
        </Card>
      )}
      <div ref={endRef} />
    </div>
  );
}

function ResultCard({ entry }: { entry: Entry }) {
  const { prompt, turn, error } = entry;
  const rows = extractRows(turn?.output);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">{prompt}</CardTitle>
        {turn && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Badge variant={turn.status === "ok" ? "default" : "destructive"}>{turn.status}</Badge>
            <span className="text-muted-foreground text-xs tabular-nums">{turn.duration_ms} ms</span>
            {turn.repairs > 0 && (
              <Badge variant="outline" className="text-[10px]">
                {turn.repairs} auto-repair{turn.repairs > 1 ? "s" : ""}
              </Badge>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {error && <p className="text-destructive text-sm">{error}</p>}
        {turn?.explanation && (
          <p className="text-muted-foreground mb-3 text-sm leading-relaxed">{turn.explanation}</p>
        )}
        {turn?.error && (
          <pre className="bg-destructive/10 text-destructive mb-3 overflow-x-auto rounded-md p-3 text-xs">
            {turn.error}
          </pre>
        )}

        {turn && (
          <Tabs defaultValue={turn.figures.length ? "charts" : rows ? "results" : "code"}>
            <TabsList>
              {rows && <TabsTrigger value="results">Results</TabsTrigger>}
              {turn.figures.length > 0 && (
                <TabsTrigger value="charts">Charts ({turn.figures.length})</TabsTrigger>
              )}
              <TabsTrigger value="code">
                <Code2 className="size-3.5" /> Code
              </TabsTrigger>
              {turn.stdout && (
                <TabsTrigger value="stdout">
                  <Terminal className="size-3.5" /> Output
                </TabsTrigger>
              )}
            </TabsList>

            {rows && (
              <TabsContent value="results">
                <ResultTable rows={rows} />
              </TabsContent>
            )}

            {turn.figures.length > 0 && (
              <TabsContent value="charts" className="space-y-3">
                {turn.figures.map((figure, index) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={index}
                    src={`data:image/png;base64,${figure}`}
                    alt={`Chart ${index + 1}`}
                    className="w-full rounded-md border bg-white"
                  />
                ))}
              </TabsContent>
            )}

            <TabsContent value="code">
              <pre className="bg-muted overflow-x-auto rounded-md p-3 text-xs leading-relaxed">
                <code>{turn.code}</code>
              </pre>
            </TabsContent>

            {turn.stdout && (
              <TabsContent value="stdout">
                <pre className="bg-muted overflow-x-auto rounded-md p-3 text-xs">{turn.stdout}</pre>
              </TabsContent>
            )}
          </Tabs>
        )}

        {turn?.status === "ok" && !rows && !turn.figures.length && (
          <pre className="bg-muted overflow-x-auto rounded-md p-3 text-xs">
            {JSON.stringify(turn.output, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}

/** Strategies are asked to put rankings under "rows"; anything else renders as JSON. */
function extractRows(output: unknown): Record<string, unknown>[] | null {
  if (!output || typeof output !== "object") return null;
  const rows = (output as { rows?: unknown }).rows;
  if (!Array.isArray(rows) || !rows.length) return null;
  if (typeof rows[0] !== "object" || rows[0] === null) return null;
  return rows as Record<string, unknown>[];
}

function ResultTable({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column} className="whitespace-nowrap">
                {column.replace(/_/g, " ")}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={index}>
              {columns.map((column) => (
                <TableCell key={column} className="whitespace-nowrap tabular-nums">
                  {formatCell(row[column])}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
