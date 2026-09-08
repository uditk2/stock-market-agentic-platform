"use client";

import { useCallback, useState } from "react";
import {
  AlertTriangle,
  Check,
  ExternalLink,
  KeyRound,
  Loader2,
  Lock,
  LogIn,
  LogOut,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePoll } from "@/hooks/use-poll";
import {
  api,
  type BrokerStatus,
  type CredentialField,
  type CredentialSource,
} from "@/lib/api";
import { ago } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_POLL_MS = 10000;
/** The code rotates every 30s, so poll fast enough that it is never stale. */
const TOTP_POLL_MS = 2000;
/** The proxy is a network hop away and rarely changes; a slow poll is plenty. */
const MODELS_POLL_MS = 30000;

type Outcome = { ok: boolean; message: string } | null;

const SOURCE_LABEL: Record<CredentialSource, string> = {
  store: "set here",
  env: "from .env",
  unset: "not set",
};

/**
 * The whole tab is behind the passphrase, so this component is really two
 * screens: the lock, and everything else. Nothing below the lock is rendered
 * or fetched until there is a session, because every endpoint it would call
 * answers 401 anyway.
 */
export function Admin() {
  const { data: session, refresh: refreshSession } = usePoll(
    () => api.adminSession(),
    STATUS_POLL_MS,
  );

  if (!session) return null;
  if (!session.enabled) return <NoPassphraseSet />;
  if (!session.authenticated) return <LockScreen onUnlocked={refreshSession} />;
  return <Unlocked onLocked={refreshSession} />;
}

/**
 * Fails closed, and says how to open it. Without a passphrase the admin API
 * refuses everything, so there is nothing to show and no login worth offering.
 */
function NoPassphraseSet() {
  return (
    <Card className="max-w-3xl border-amber-500/40">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="size-4 text-amber-600" />
          Admin is disabled
        </CardTitle>
        <CardDescription>
          This page manages broker credentials, so it is not served without a passphrase
          to protect it.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p>
          Set <code>LIVEGRAPH_ADMIN_PASSWORD</code> in <code>.env</code> and restart:
        </p>
        <pre className="bg-muted overflow-x-auto rounded-md p-3 text-xs">
          LIVEGRAPH_ADMIN_PASSWORD=something-only-you-know
        </pre>
        <p className="text-muted-foreground">
          Running in Docker, <code>docker compose up -d --force-recreate</code> picks it up.
          Everything else in the app works without it — only this tab is affected.
        </p>
      </CardContent>
    </Card>
  );
}

function LockScreen({ onUnlocked }: { onUnlocked: () => void }) {
  const [passphrase, setPassphrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unlock = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.adminLogin(passphrase);
      setPassphrase("");
      onUnlocked();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Lock className="size-4" />
          Admin
        </CardTitle>
        <CardDescription>
          Broker credentials and the model proxy live here. Enter the admin passphrase to
          continue.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (passphrase) unlock();
          }}
        >
          <Input
            type="password"
            autoComplete="current-password"
            autoFocus
            placeholder="Admin passphrase"
            value={passphrase}
            onChange={(event) => setPassphrase(event.target.value)}
          />
          {error && (
            <p className="rounded-md border border-rose-500/30 bg-rose-500/5 px-3 py-2 text-sm">
              {error}
            </p>
          )}
          <Button type="submit" disabled={busy || !passphrase} className="w-full">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
            Unlock
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Unlocked({ onLocked }: { onLocked: () => void }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Outcome>(null);
  const { data: status, refresh } = usePoll(() => api.brokerStatus(), STATUS_POLL_MS);
  const { data: totp } = usePoll(() => api.brokerTotp(), TOTP_POLL_MS);
  const { data: models } = usePoll(() => api.modelStatus(), MODELS_POLL_MS);

  /** Every write shares this: one busy flag, one message, one refresh. */
  const run = useCallback(
    async (action: () => Promise<string>) => {
      setBusy(true);
      setResult(null);
      try {
        setResult({ ok: true, message: await action() });
      } catch (error) {
        setResult({ ok: false, message: error instanceof Error ? error.message : String(error) });
      } finally {
        setBusy(false);
        refresh();
      }
    },
    [refresh],
  );

  if (!status) return null;
  const live = status.feed_mode === "live";

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center gap-3">
        <Badge
          variant="outline"
          className="border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
        >
          Unlocked
        </Badge>
        <Button
          size="sm"
          variant="ghost"
          className="ml-auto"
          onClick={async () => {
            await api.adminLogout();
            onLocked();
          }}
        >
          <LogOut className="size-4" />
          Lock
        </Button>
      </div>

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
          </div>

          <BrokerLogin
            status={status}
            totpAvailable={Boolean(totp?.available)}
            busy={busy}
            onLogin={(code) => run(async () => (await api.brokerLogin(code)).message)}
          />

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

      <CredentialsForm
        fields={status.credentials}
        secretUnusable={Boolean(totp && !totp.available && status.credentials.some(
          (f) => f.name === "totp_secret" && f.set,
        ))}
        busy={busy}
        onSave={(values) =>
          run(async () => (await api.saveCredentials(values)).message)
        }
      />

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
          <CardTitle className="text-base">Model access</CardTitle>
          <CardDescription>
            Agents reach Claude and Codex through CLIProxyAPI, which fronts your existing
            subscriptions, so no provider API key is involved. The OAuth logins belong to
            the proxy and are done in its own control panel, not here.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!models ? (
            <p className="text-muted-foreground text-sm">Checking…</p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant="outline"
                  className={cn(
                    models.reachable && models.key_accepted
                      ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                      : "border-amber-500/40 text-amber-700 dark:text-amber-400",
                  )}
                >
                  {!models.reachable
                    ? "No proxy reachable"
                    : !models.key_accepted
                      ? "Key rejected"
                      : "Connected"}
                </Badge>
                <code className="text-muted-foreground text-[11px]">{models.base_url}</code>
                <Button size="sm" variant="outline" className="ml-auto" asChild>
                  <a href={models.control_panel_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="size-3.5" />
                    Control panel
                  </a>
                </Button>
              </div>

              <p className="text-muted-foreground text-sm">{models.detail}</p>

              <div className="divide-y border-t pt-1">
                {models.models.map((model) => (
                  <div key={model.role} className="flex items-start gap-3 py-2">
                    {model.available ? (
                      <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                    ) : (
                      <X className="mt-0.5 size-4 shrink-0 text-amber-600" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium">{model.role}</span>
                        <code className="text-muted-foreground text-[11px]">{model.name}</code>
                      </div>
                      {!model.available && (
                        <p className="text-muted-foreground text-xs">
                          {models.reachable
                            ? "The proxy does not advertise this model. Add the matching account in its control panel."
                            : "Cannot tell while the proxy is unreachable."}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * The daily login.
 *
 * Kotak's session expires overnight, so this is the first thing done each
 * trading morning. The code can come from a stored secret or from the
 * authenticator in your hand; the app only needs the secret to log itself back
 * in unattended, so a typed code is a complete substitute here.
 */
function BrokerLogin({
  status,
  totpAvailable,
  busy,
  onLogin,
}: {
  status: BrokerStatus;
  totpAvailable: boolean;
  busy: boolean;
  onLogin: (code?: string) => Promise<void>;
}) {
  const [code, setCode] = useState("");

  //: Everything but the secret. A code typed here stands in for it.
  const missing = status.credentials.filter((f) => !f.set && f.name !== "totp_secret");
  if (missing.length) {
    return (
      <p className="text-muted-foreground text-sm">
        Login needs {missing.map((f) => f.label).join(", ")}. Fill them in below first.
      </p>
    );
  }

  if (totpAvailable) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" disabled={busy} onClick={() => onLogin()}>
          {busy ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
          Log in now
        </Button>
        <span className="text-muted-foreground text-sm">
          Using the code derived from your stored secret.
        </span>
      </div>
    );
  }

  return (
    <form
      className="space-y-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (code.length === 6) onLogin(code).then(() => setCode(""));
      }}
    >
      <Label htmlFor="totp-code" className="text-sm font-medium">
        Six-digit code from your authenticator
      </Label>
      <div className="flex flex-wrap items-center gap-3">
        <Input
          id="totp-code"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          maxLength={6}
          className="max-w-[9rem] font-mono text-lg tracking-[0.3em] tabular-nums"
          value={code}
          //: Digits only, so a pasted code with spaces still submits.
          onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
        />
        <Button type="submit" size="sm" disabled={busy || code.length !== 6}>
          {busy ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
          Log in
        </Button>
      </div>
      <p className="text-muted-foreground text-xs">
        No TOTP secret is stored, so the code is typed each morning. Store the secret
        below to have the app derive it instead.
      </p>
    </form>
  );
}


/**
 * All five credentials as one form.
 *
 * Every input starts empty rather than pre-filled, because the values cannot be
 * read back — the API returns presence, never content. An empty box therefore
 * means "leave this alone", which is also what makes it safe to submit the form
 * after changing only one field. The state of each field is stated beside its
 * label instead, since the input itself can no longer show it.
 */
function CredentialsForm({
  fields,
  secretUnusable,
  busy,
  onSave,
}: {
  fields: CredentialField[];
  //: A stored secret that will not produce a code. It passes every presence
  //: check, so without saying so here the row reads as correctly configured
  //: while the login it is supposed to serve keeps failing.
  secretUnusable: boolean;
  busy: boolean;
  onSave: (values: Record<string, string>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const filled = Object.entries(values).filter(([, value]) => value.trim());

  const submit = async () => {
    await onSave(Object.fromEntries(filled));
    setValues({});
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Broker credentials</CardTitle>
        <CardDescription>
          Values are never sent to the browser, only whether each one is present and where
          it came from. Anything saved here is written to the app&apos;s state directory,
          takes precedence over <code>.env</code>, and survives a rebuild. Leave a box
          empty to keep the current value. The TOTP secret is optional: it is the long
          base32 string from the one-time QR registration, and storing it only saves
          typing a code each morning.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (filled.length) submit();
          }}
        >
          {fields.map((field) => (
            <div key={field.name} className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                {field.set ? (
                  <Check className="size-3.5 shrink-0 text-emerald-600" />
                ) : (
                  <X className="text-muted-foreground size-3.5 shrink-0" />
                )}
                <Label htmlFor={field.name} className="text-sm font-medium">
                  {field.label}
                </Label>
                <code className="text-muted-foreground text-[11px]">
                  KOTAK_{field.name.toUpperCase()}
                </code>
                <Badge variant="outline" className="text-muted-foreground text-[10px]">
                  {SOURCE_LABEL[field.source]}
                </Badge>
                {field.name === "totp_secret" && (
                  <Badge variant="outline" className="text-muted-foreground text-[10px]">
                    optional
                  </Badge>
                )}
                {field.placeholder && (
                  <Badge
                    variant="outline"
                    className="border-amber-500/40 text-amber-700 dark:text-amber-400"
                  >
                    looks like a comment, not a value
                  </Badge>
                )}
                {field.name === "totp_secret" && field.set && secretUnusable && (
                  <Badge
                    variant="outline"
                    className="border-amber-500/40 text-amber-700 dark:text-amber-400"
                  >
                    stored, but not a usable secret
                  </Badge>
                )}
              </div>
              <Input
                id={field.name}
                type="password"
                autoComplete="off"
                placeholder={field.set ? "Leave empty to keep the current value" : field.hint}
                value={values[field.name] ?? ""}
                onChange={(event) =>
                  setValues((current) => ({ ...current, [field.name]: event.target.value }))
                }
              />
              <p className="text-muted-foreground text-xs">{field.hint}</p>
            </div>
          ))}

          <div className="flex items-center gap-3 border-t pt-4">
            <Button type="submit" disabled={busy || !filled.length}>
              {busy && <Loader2 className="size-4 animate-spin" />}
              Save {filled.length ? `${filled.length} value${filled.length > 1 ? "s" : ""}` : ""}
            </Button>
            {filled.length > 0 && (
              <Button type="button" variant="ghost" onClick={() => setValues({})}>
                Clear form
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
