// Typed client for the Python FastAPI backend (Phase 2 of the
// web-adapter migration).  All ML computation lives on the backend (:9000);
// the Next.js route handlers are thin proxies using this module.

import type { BacktestConfig, BacktestSummary, Draw, PredictionResult, ProductName } from "./types";

/** Base URL of the Python backend; configurable via the API_URL env var. */
export const API_URL: string = process.env.API_URL ?? "http://localhost:9000";

// ---------- backend response types (subset we consume) ----------

/** ``GET /api/products/{name}`` payload (snake_case). */
export interface BackendProductInfo {
  name: string;
  min: number;
  max: number;
  size_output: number;
  has_special: boolean;
  special_min: number;
  special_max: number;
  special_count: number;
  ticket_price: number;
  interval_days: number | null;
}

/** ``GET /api/draws`` payload. */
export interface DrawsResponse {
  product: string;
  display: string;
  total: number;
  draws: Draw[];
}

/** Product catalog entry as consumed by ``page.tsx`` / ``Sidebar``. */
export interface ProductCatalogItem {
  name: ProductName;
  display: string;
  minValue: number;
  maxValue: number;
  sizeOutput: number;
  hasSpecial: boolean;
  specialMin: number;
  specialMax: number;
  defaultConfig: BacktestConfig;
}

// ---------- default config mapping ----------

/**
 * Default Steiner ``v`` (pool size) per product — mirrors the
 * ``steinerSystem`` triple column of the old ``web/src/lib/config.ts``.
 */
const DEFAULT_STEINER_V: Record<ProductName, number> = {
  power_535: 35,
  power_645: 45,
  power_655: 55,
  keno: 45,
  "3d": 10,
  "3d_pro": 10,
  bingo18: 10,
};

/**
 * Default backtest config (spec: ``web/src/lib/backtest.ts::getDefaultBacktestConfig``).
 * The Python backend merges deep-ish over these same defaults, so a
 * partial UI config is safe to pass through.
 */
export function getDefaultBacktestConfig(name: ProductName): BacktestConfig {
  return {
    tpd: 2,
    cold: { lookbackDays: 365, selectionWeight: 0.7 },
    steiner: {
      lookbackDays: 365,
      filterConsecutive: true,
      filterSameDecade: true,
      t: 2,
      k: 3,
      v: DEFAULT_STEINER_V[name] ?? 45,
    },
    inverse: { topK: 15, rankOrder: "desc" },
    specials: { topN: 4, mode: "markov_steiner", lookbackDraws: 60, offsetDraws: 30 },
    ddFilter: { enabled: true, threshold: 15_000_000_000 },
    dateFrom: null,
    dateTo: null,
  };
}

/** Products the UI supports end-to-end (Power family: result is a plain int list). */
const POWER_FAMILY: readonly string[] = ["power_535", "power_645", "power_655"];

const DEFAULT_DISPLAYS: Partial<Record<ProductName, string>> = {
  power_535: "Power 5/35",
  power_645: "Power 6/45",
  power_655: "Power 6/55",
  keno: "Keno",
  "3d": "Vietlott 3D",
  "3d_pro": "Vietlott 3D Pro",
  bingo18: "Bingo18",
};

// ---------- typed fetch helpers ----------

/**
 * Fetch the product catalog from the backend and merge it into the shape
 * the UI consumers expect (``{products: ProductCatalogItem[]}``).
 */
export async function fetchProducts(): Promise<ProductCatalogItem[]> {
  const names = (await fetchJson(`${API_URL}/api/products`)) as string[];
  const items: ProductCatalogItem[] = [];
  for (const name of names) {
    const info = (await fetchJson(`${API_URL}/api/products/${name}`)) as BackendProductInfo;
    items.push({
      name: name as ProductName,
      display: DEFAULT_DISPLAYS[name as ProductName] ?? name,
      minValue: info.min,
      maxValue: info.max,
      sizeOutput: info.size_output,
      hasSpecial: info.has_special,
      specialMin: info.special_min,
      specialMax: info.special_max,
      defaultConfig: getDefaultBacktestConfig(name as ProductName),
    });
  }
  return items.filter((p) => POWER_FAMILY.includes(p.name));
}

/** Fetch the newest-first draw (and optional prize) history. */
export async function fetchDraws(
  product: ProductName,
  limit: number,
  includePrizes: boolean,
): Promise<DrawsResponse> {
  const params = new URLSearchParams({ product, limit: String(limit), prizes: includePrizes ? "1" : "0" });
  return (await fetchJson(
    `${API_URL}/api/draws?${params.toString()}`,
  )) as DrawsResponse;
}

/** Generate next-draw tickets on the backend (returns the TS PredictionResult shape). */
export async function fetchPredict(
  product: ProductName,
  config: BacktestConfig,
): Promise<PredictionResult> {
  return (await postJson(`${API_URL}/api/predict`, {
    product,
    strategy: config.strategy ?? "Inverse Hybrid: Cold Numbers → Steiner",
    config,
  })) as PredictionResult;
}

/** Estimate per-ticket EV on the backend (returns the TS EvResponse shape). */
export async function fetchEv(body: {
  product: ProductName;
  numTickets?: number;
  jackpotBase?: number;
  historyLimit?: number;
  historyEndId?: string;
  tierMode?: "fixed" | "historical_mean";
}): Promise<Record<string, unknown>> {
  return (await postJson(`${API_URL}/api/ev`, {
    product: body.product,
    numTickets: body.numTickets ?? 8,
    jackpotBase: body.jackpotBase ?? 6_000_000_000,
    historyLimit: body.historyLimit ?? 10,
    historyEndId: body.historyEndId ?? undefined,
    tierMode: body.tierMode ?? "fixed",
  })) as Record<string, unknown>;
}

/** Run the flat-strategy backtest on the backend (returns the TS BacktestSummary shape). */
export async function fetchBacktest(
  product: ProductName,
  config: BacktestConfig,
): Promise<BacktestSummary> {
  return (await postJson(
    `${API_URL}/api/backtest/strategy`,
    { product, config },
  )) as BacktestSummary;
}

// ---------- low-level helpers ----------

/** GET a JSON endpoint, raising on non-2xx with the backend's error detail. */
export async function fetchJson(url: string, init?: RequestInit): Promise<unknown> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { detail?: string; error?: string };
    throw new Error(data.detail ?? data.error ?? `HTTP ${res.status}`);
  }
  return res.json();
}

/** POST a JSON body, raising on non-2xx with the backend's error detail. */
export async function postJson(url: string, body: unknown): Promise<unknown> {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
