"use client";

/**
 * Live tick subscription.
 *
 * The socket sends a full snapshot on connect and coalesced batches after, so
 * this keeps one map keyed by symbol and merges each batch into it. Reconnects
 * with backoff, because a dropped socket must not silently freeze the prices
 * on screen: `connected` is surfaced so the UI can say so.
 */

import { useEffect, useRef, useState } from "react";

import { wsUrl, type Quote } from "@/lib/api";

interface TickFrame {
  type: "snapshot" | "ticks";
  ticks: {
    symbol: string;
    ltp: number;
    change_pct: number | null;
    open_interest: number | null;
    volume: number | null;
    ts: number;
  }[];
}

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

export function useTicks() {
  const [ticks, setTicks] = useState<Record<string, Quote>>({});
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      const socket = new WebSocket(wsUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        setConnected(true);
      };

      socket.onmessage = (event) => {
        const frame = JSON.parse(event.data) as TickFrame;
        setTicks((current) => {
          const next = frame.type === "snapshot" ? {} : { ...current };
          for (const tick of frame.ticks) {
            next[tick.symbol] = {
              ...tick,
              segment: "nse_fo",
            } as Quote;
          }
          return next;
        });
      };

      socket.onclose = () => {
        setConnected(false);
        if (disposed) return;
        // Backoff, capped, so a backend restart reconnects without hammering it.
        const delay = Math.min(
          RECONNECT_MAX_MS,
          RECONNECT_BASE_MS * 2 ** attemptRef.current,
        );
        attemptRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => socket.close();
    };

    connect();
    return () => {
      disposed = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      socketRef.current?.close();
    };
  }, []);

  return { ticks, connected };
}
