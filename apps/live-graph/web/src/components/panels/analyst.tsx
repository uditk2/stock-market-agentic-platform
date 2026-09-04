"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, MessageSquare, Send, Wrench } from "lucide-react";

import { Empty } from "@/components/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

interface Turn {
  role: "you" | "analyst";
  text: string;
  tools?: string[];
}

const SUGGESTIONS = [
  "What is diverging most from its peers right now, and does the graph explain it?",
  "If crude rises, which F&O names does the graph say suffer most?",
  "Which sector has the widest spread between its best and worst member?",
];

export function Analyst({ selected }: { selected: string | null }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  const send = async (question: string) => {
    if (!question.trim() || busy) return;
    setTurns((t) => [...t, { role: "you", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const reply = await api.ask(question, threadId);
      setThreadId(reply.thread_id);
      setTurns((t) => [...t, { role: "analyst", text: reply.text, tools: reply.tools_used }]);
    } catch (error) {
      setTurns((t) => [
        ...t,
        { role: "analyst", text: error instanceof Error ? error.message : String(error) },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex h-[calc(100vh-13rem)] flex-col">
      <CardHeader>
        <CardTitle>Analyst</CardTitle>
        <CardDescription>
          Answers come from graph and price tools, not from memory. It will say when
          the graph does not explain a move.
        </CardDescription>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col gap-4">
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
          {!turns.length ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <Empty
                title="Ask about what is moving"
                hint="Every number in an answer comes from a tool call."
                icon={<MessageSquare className="size-6" />}
              />
              <div className="flex max-w-lg flex-col gap-2">
                {(selected
                  ? [`Why is ${selected} moving? Use the graph.`, ...SUGGESTIONS]
                  : SUGGESTIONS
                ).map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="outline"
                    size="sm"
                    className="h-auto justify-start whitespace-normal py-2 text-left text-xs"
                    onClick={() => send(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            turns.map((turn, index) => (
              <div
                key={index}
                className={turn.role === "you" ? "flex justify-end" : "flex justify-start"}
              >
                <div
                  className={
                    turn.role === "you"
                      ? "bg-primary text-primary-foreground max-w-[80%] rounded-lg px-3 py-2 text-sm"
                      : "bg-muted max-w-[85%] rounded-lg px-3 py-2"
                  }
                >
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{turn.text}</p>
                  {turn.tools && turn.tools.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-1">
                      <Wrench className="text-muted-foreground size-3" />
                      {turn.tools.map((tool) => (
                        <Badge key={tool} variant="outline" className="font-mono text-[10px]">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {busy && (
            <div className="text-muted-foreground flex items-center gap-2 text-sm">
              <Loader2 className="size-4 animate-spin" /> Reading the graph…
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask about a move, a sector, or a propagation path…"
            className="max-h-32 min-h-[44px] resize-none"
            rows={1}
          />
          <Button onClick={() => send(input)} disabled={busy || !input.trim()} size="icon" className="size-11 shrink-0">
            <Send className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
