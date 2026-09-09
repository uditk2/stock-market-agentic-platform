/**
 * Typed client for the livegraph API.
 *
 * Every field the backend sends is optional-safe here: prices arrive
 * asynchronously, so a symbol can exist in the graph with no quote yet.
 */

/**
 * The backend serves this UI, so calls are same-origin by default and need no
 * configuration. NEXT_PUBLIC_API_URL overrides it for running the dev server
 * against a backend on another port.
 */
const CONFIGURED = process.env.NEXT_PUBLIC_API_URL ?? "";
const BASE = CONFIGURED || (typeof window === "undefined" ? "" : window.location.origin);

export type FeedMode = "live" | "unconfigured" | "error" | "injected";

export interface FeedStatus {
  mode: FeedMode;
  connected: boolean;
  instruments: number;
  symbols_priced: number;
  detail: string;
}

export interface Quote {
  symbol: string;
  ltp: number;
  change_pct: number | null;
  open_interest: number | null;
  volume: number | null;
  segment: string;
  ts: number;
}

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  type: "stock" | "sector" | "macro";
  sector: string | null;
  fo: boolean;
  peer_groups: string[];
  change_pct: number | null;
  ltp: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  sign: number;
  strength: number;
  note: string | null;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface EdgeProposal {
  source: string;
  target: string;
  correlation: number;
  samples: number;
  same_sector: boolean;
  confidence: "low" | "moderate" | "high";
}

export interface SectorRow {
  sector: string;
  members: number;
  priced: number;
  avg_change_pct: number;
  advancing: number;
  declining: number;
}

export interface ImpactRow {
  symbol: string;
  expected: string;
  relative_magnitude: number;
  hops: number;
  path: string;
  actual_change_pct: number | null;
}

/** A "roundup" lists several unrelated companies, so its tags name them
 *  separately and never pair them. */
export type NewsKind = "single" | "roundup";

export interface NewsItem {
  title: string;
  link: string;
  summary: string;
  ts: number;
  source: string;
  entities: Record<string, string>;
  fo: boolean;
  kind: NewsKind;
}

export type VerdictKey = "unexplained" | "conflicted" | "stock_specific" | "sector_wide";

export interface Mover {
  symbol: string;
  name: string;
  sector: string | null;
  ltp: number;
  change_pct: number;
  verdict: VerdictKey;
  verdict_label: string;
}

export interface MoversPayload {
  gainers: Mover[];
  losers: Mover[];
  sectors: SectorRow[];
}

export interface Peer {
  symbol: string;
  change_pct: number;
  vs_peer_avg: number;
}

export interface SectorContext {
  name: string;
  avg_change_pct: number;
  advancing: number;
  declining: number;
  breadth: number;
  one_sided: boolean;
}

export interface Driver {
  edge_type: string;
  node: string;
  sign: number;
  strength: number;
  note: string | null;
  driver_change_pct: number | null;
  expected_direction: number;
  conflicting: boolean;
}

export interface ScopedNews {
  scope: "stock" | "sector" | "market" | "web";
  title: string;
  source: string;
  ts: number;
  link: string;
  matched_node: string | null;
  roundup: boolean;
}

export interface Narration {
  text: string;
  written_at: number;
  from_cache: boolean;
  refreshed_because: string | null;
}

export interface StockScan {
  symbol: string;
  name: string;
  sector: string | null;
  peer_groups: string[];
  ltp: number;
  change_pct: number;
  verdict: VerdictKey;
  verdict_label: string;
  why: string;
  evidence: {
    change_pct: number;
    peer_avg: number | null;
    peer_count: number;
    gap: number | null;
    news_counts: Record<string, number>;
  };
  sector_context: SectorContext | null;
  peers: Peer[];
  drivers: Driver[];
  news: ScopedNews[];
  narration: Narration | null;
}

export interface SectorDetail {
  sector: SectorContext;
  members: Mover[];
}

export type CredentialSource = "store" | "env" | "unset";

export interface CredentialField {
  name: string;
  label: string;
  set: boolean;
  placeholder: boolean;
  hint: string;
  source: CredentialSource;
  /** Why a field that is set will still not work. Never contains the value. */
  problem: string | null;
}

export interface TotpState {
  available: boolean;
  code: string | null;
  expires_in: number | null;
  error: string | null;
}

export interface BrokerStatus {
  feed_mode: string;
  feed_detail: string;
  configured: boolean;
  credentials: CredentialField[];
  session_active: boolean;
  session_since: number | null;
  last_error: string | null;
  totp: TotpState;
}

export interface ModelAvailability {
  role: string;
  name: string;
  available: boolean;
}

export interface ModelStatus {
  base_url: string;
  reachable: boolean;
  key_accepted: boolean;
  key_set: boolean;
  control_panel_url: string;
  detail: string;
  models: ModelAvailability[];
}

export interface AdminSession {
  enabled: boolean;
  authenticated: boolean;
}

export interface CredentialsResult {
  ok: boolean;
  changed: string[];
  message: string;
  configured: boolean;
}

export interface AnalystReply {
  text: string;
  thread_id: string;
  tools_used: string[];
}

export interface ScratchpadTurn {
  thread_id: string;
  status: string;
  code: string;
  explanation: string;
  output: unknown;
  figures: string[];
  stdout: string;
  error: string;
  repairs: number;
  duration_ms: number;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json() as Promise<T>;
}

async function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorMessage(response, path));
  return response.json() as Promise<T>;
}

const post = <T,>(path: string, body?: unknown) => send<T>("POST", path, body);

/**
 * FastAPI puts the readable reason in `detail`. Surfacing the raw JSON instead
 * would show an operator `{"detail":"Wrong passphrase."}` in a toast.
 */
async function errorMessage(response: Response, path: string): Promise<string> {
  const raw = await response.text();
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.detail === "string") return parsed.detail;
  } catch {
    /* not JSON; fall through to the raw body */
  }
  return raw || `${response.status} ${path}`;
}

export const api = {
  status: () => get<FeedStatus>("/api/market/status"),
  movers: (perSide: number) => get<MoversPayload>(`/api/scan/movers?per_side=${perSide}`),
  stockScan: (symbol: string, opts: { searchWeb?: boolean; narrate?: boolean } = {}) =>
    get<StockScan>(
      `/api/scan/stock/${symbol}?search_web=${opts.searchWeb ?? false}` +
        `&narrate=${opts.narrate ?? true}`,
    ),
  brokerStatus: () => get<BrokerStatus>("/api/admin/broker"),
  brokerTotp: () => get<TotpState>("/api/admin/broker/totp"),
  brokerLogin: (secrets: { totp?: string; mpin?: string }) =>
    post<{ ok: boolean; message: string; session_since: number | null }>(
      "/api/admin/broker/login",
      { totp: secrets.totp ?? null, mpin: secrets.mpin ?? null },
    ),
  saveCredentials: (values: Record<string, string>) =>
    send<CredentialsResult>("PUT", "/api/admin/broker/credentials", { values }),
  modelStatus: () => get<ModelStatus>("/api/admin/models"),
  adminSession: () => get<AdminSession>("/api/admin/session"),
  adminLogin: (passphrase: string) =>
    post<AdminSession>("/api/admin/session", { passphrase }),
  adminLogout: () => send<AdminSession>("DELETE", "/api/admin/session"),
  sectorDetail: (name: string) =>
    get<SectorDetail>(`/api/scan/sector/${encodeURIComponent(name)}`),
  quotes: () => get<Quote[]>("/api/market/quotes"),
  edgeProposals: (limit = 20) =>
    get<EdgeProposal[]>(`/api/market/edge-proposals?limit=${limit}`),
  graph: (foOnly = true, includeSectors = false) =>
    get<GraphPayload>(`/api/graph?fo_only=${foOnly}&include_sectors=${includeSectors}`),
  neighbourhood: (symbol: string, depth = 1) =>
    get<GraphPayload>(`/api/graph/node/${symbol}?depth=${depth}`),
  impact: (origin: string, direction: "up" | "down") =>
    get<ImpactRow[]>(`/api/graph/impact/${origin}?direction=${direction}`),
  sectors: () => get<SectorRow[]>("/api/graph/sectors"),
  news: (limit = 50, foOnly = false) =>
    get<NewsItem[]>(`/api/news?limit=${limit}&fo_only=${foOnly}`),
  newsFor: (symbol: string) => get<NewsItem[]>(`/api/news/symbol/${symbol}`),
  refreshNews: () => post<{ started: boolean }>("/api/news/refresh"),
  ask: (question: string, threadId?: string | null) =>
    post<AnalystReply>("/api/analyst/ask", { question, thread_id: threadId ?? null }),
  explain: (symbol: string) => post<AnalystReply>(`/api/analyst/explain/${symbol}`),
  reviewEdgeProposals: () => post<AnalystReply>("/api/analyst/review-edge-proposals"),
  scratchpadHealth: () =>
    get<{ sandbox_available: boolean; detail: string }>("/api/scratchpad/health"),
  scratchpadSend: (prompt: string, threadId?: string | null) =>
    post<ScratchpadTurn>("/api/scratchpad/send", { prompt, thread_id: threadId ?? null }),
  scratchpadRerun: (threadId: string) =>
    post<ScratchpadTurn>(`/api/scratchpad/rerun/${threadId}`),
};

export const wsUrl = () => `${BASE.replace(/^http/, "ws")}/ws/ticks`;

export const apiBase = () => BASE;
