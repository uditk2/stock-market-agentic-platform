"use client";

import { Activity, AlertTriangle, FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { FeedStatus } from "@/lib/api";

/**
 * Whether prices are real is the most important fact on the page, so it is
 * stated permanently in the header rather than buried in a settings view.
 */
export function FeedBadge({
  status,
  socketConnected,
}: {
  status: FeedStatus | null;
  socketConnected: boolean;
}) {
  if (!status) {
    return <Badge variant="outline" className="gap-1.5">Connecting…</Badge>;
  }

  const simulated = status.mode === "simulated";
  const label = simulated ? "Simulated data" : "Live · Kotak Neo";

  return (
    <div className="flex items-center gap-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant={simulated ? "secondary" : "default"}
            className={
              simulated
                ? "gap-1.5 border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400"
                : "gap-1.5 border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
            }
          >
            {simulated ? (
              <FlaskConical className="size-3" />
            ) : (
              <Activity className="size-3" />
            )}
            {label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          {simulated
            ? `These prices are generated, not real. ${status.detail}`
            : status.detail}
        </TooltipContent>
      </Tooltip>

      <span className="text-muted-foreground text-xs tabular-nums">
        {status.symbols_priced}/{status.instruments} priced
      </span>

      {!socketConnected && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className="gap-1.5 border-rose-500/40 text-rose-600">
              <AlertTriangle className="size-3" />
              Stream down
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            The tick socket is disconnected, so prices on screen are frozen.
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}
