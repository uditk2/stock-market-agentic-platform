"use client";

import { useState } from "react";
import { AlertTriangle, Check, KeyRound, Loader2, LogIn, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { usePoll } from "@/hooks/use-poll";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_POLL_MS = 10000;
/** The code rotates every 30s, so poll fast enough that it is never stale. */
const TOTP_POLL_MS = 2000;

export function Admin() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const { data: status, refresh } = usePoll(() => api.brokerStatus(), STATUS_POLL_MS);
  const { data: totp } = usePoll(() => api.brokerTotp(), TOTP_POLL_MS);

  const login = async () => {
    setBusy(true);
    setResult(null);
    try {
      const reply = await api.brokerLogin();
      setResult({ ok: true, message: reply.message });
      refresh();
    } catch (error) {
      setResult({ ok: false, message: error instanceof Error ? error.message : String(error) });
    } finally {
      setBusy(false);
    }
  };

  if (!status) return null;
  const live = status.feed_mode === "live";

  return (
    <div className="max-w-3xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Kotak Neo session</CardTitle>
          <CardDescription>
            Sessions expire daily, so a fresh login is needed each trading day. The TOTP
            code below is derived from your registered secret and rotates every 30 seconds;
            it is not something you generate or paste in.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge
              variant="outline"
              className={cn(
                status.session_active
                  ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                  : "border-muted-foreground/30 text-muted-foreground",
              )}
            >
              {status.session_active ? "Session active" : "No session"}
            </Badge>
            {status.session_since && (
              <span className="text-muted-foreground text-xs">
                since {ago(status.session_since)}
              </span>
            )}
            <Badge
              variant="outline"
              className={cn(
                live
                  ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                  : "border-amber-500/40 text-amber-700 dark:text-amber-400",
              )}
            >
              Feed: {status.feed_mode}
            </Badge>
            <Button
              size="sm"
              className="ml-auto"
              onClick={login}
              disabled={busy || !status.configured}
            >
              {busy ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
              Log in now
            </Button>
          </div>

          {!status.configured && (
            <p className="text-muted-foreground text-sm">
              Fill the missing values in <code>.env</code> and restart. Login stays disabled
              until all five are present.
            </p>
          )}

          {result && (
            <p
              className={cn(
                "rounded-md border px-3 py-2 text-sm",
                result.ok
                  ? "border-emerald-500/30 bg-emerald-500/5"
                  : "border-rose-500/30 bg-rose-500/5",
              )}
            >
              {result.message}
            </p>
          )}

          {status.last_error && !result && (
            <p className="text-muted-foreground rounded-md border px-3 py-2 text-xs">
              Last error: {status.last_error}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="size-4" />
            Current TOTP code
          </CardTitle>
          <CardDescription>
            Derived from the registered secret. Shown so you can confirm the secret is
            right, or complete a login by hand.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {totp?.available ? (
            <div className="flex items-baseline gap-4">
              <span className="font-mono text-3xl tracking-[0.3em] tabular-nums">
                {totp.code}
              </span>
              <span className="text-muted-foreground text-sm tabular-nums">
                rotates in {totp.expires_in}s
              </span>
            </div>
          ) : (
            <p className="text-muted-foreground flex items-start gap-2 text-sm">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" />
              {totp?.error ?? "No TOTP secret configured."}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Credentials</CardTitle>
          <CardDescription>
            Read from <code>.env</code>. Values are never sent to the browser, only whether
            each one is present.
          </CardDescription>
        </CardHeader>
        <CardContent className="divide-y">
          {status.credentials.map((field) => (
            <div key={field.name} className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0">
              {field.set ? (
                <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" />
              ) : (
                <X className="text-muted-foreground mt-0.5 size-4 shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{field.label}</span>
                  <code className="text-muted-foreground text-[11px]">
                    KOTAK_{field.name.toUpperCase()}
                  </code>
                  {field.placeholder && (
                    <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-400">
                      looks like a comment, not a value
                    </Badge>
                  )}
                </div>
                <p className="text-muted-foreground text-xs">{field.hint}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
