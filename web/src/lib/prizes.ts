// Prize calculation logic — mirrors src/vietlott/config/prizes.py.
// Includes the Power 5/35 split rule (1/3 → Giải Nhất, 1/6 → each of Nhì/Ba/Tư/Năm)
// when Độc Đắc > 12B AND Độc Đắc had no winners in that draw.

import type { ProductName, PrizeRecord } from "./types";

const CONSOLATION_NAMES: ReadonlySet<string> = new Set([
  "Giải Khuyến Khích",
  "Giải Khuyến khích",
  "Khuyến Khích",
  "Khuyến khích",
]);

// (main, special, prize_name) — first match wins.
const PRIZE_NAME_MAP: Record<string, Array<[number, number, string]>> = {
  power_535: [
    [5, 1, "Giải Độc Đắc"],
    [5, 0, "Giải Nhất"],
    [4, 1, "Giải Nhì"],
    [4, 0, "Giải Ba"],
    [3, 1, "Giải Tư"],
    [3, 0, "Giải Năm"],
  ],
  power_645: [
    [6, 0, "Jackpot"],
    [5, 0, "Giải Nhất"],
    [4, 0, "Giải Nhì"],
    [3, 0, "Giải Ba"],
  ],
  power_655: [
    [6, 0, "Jackpot 1"],
    [5, 1, "Jackpot 2"],
    [5, 0, "Giải Nhất"],
    [4, 0, "Giải Nhì"],
    [3, 0, "Giải Ba"],
  ],
};

const POWER_535_SPLIT_THRESHOLD = 12_000_000_000;
const POWER_535_STANDARD_PV: Record<string, number> = {
  "Giải Nhất": 10_000_000,
  "Giải Nhì": 5_000_000,
  "Giải Ba": 500_000,
  "Giải Tư": 100_000,
  "Giải Năm": 30_000,
};

function parseVnd(value: unknown): number {
  if (typeof value === "number") return Math.trunc(value);
  if (typeof value === "string") {
    const cleaned = value.replace(/[.,\s]/g, "");
    if (!cleaned) return 0;
    const n = Number(cleaned);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
  }
  return 0;
}

function parseWinners(value: unknown): number {
  if (typeof value === "number") return Math.trunc(value);
  if (typeof value === "string") {
    const cleaned = value.replace(/[.,\s]/g, "");
    if (!cleaned) return 0;
    const n = Number(cleaned);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
  }
  return 0;
}

function lookupPrizeName(
  product: ProductName,
  mainMatch: number,
  specialMatch: number,
): string | null {
  for (const [m, s, name] of PRIZE_NAME_MAP[product] ?? []) {
    if (m === mainMatch && s === specialMatch) return name;
  }
  if (product === "power_535" && specialMatch === 1 && mainMatch >= 0 && mainMatch <= 2) {
    return "Giải Khuyến Khích";
  }
  return null;
}

function fallbackPrize(product: ProductName, mainMatch: number, specialMatch: number): number {
  if (product === "power_535") return prizePower535(mainMatch, specialMatch);
  if (product === "power_645") return prizePower645(mainMatch, specialMatch);
  if (product === "power_655") return prizePower655(mainMatch, specialMatch);
  return 0;
}

function prizePower655(m: number, s: number): number {
  if (m === 6) return 30_000_000_000;
  if (m === 5 && s === 1) return 3_000_000_000;
  if (m === 5) return 40_000_000;
  if (m === 4) return 500_000;
  if (m === 3) return 50_000;
  return 0;
}
function prizePower645(m: number, _s: number): number {
  if (m === 6) return 12_000_000_000;
  if (m === 5) return 10_000_000;
  if (m === 4) return 300_000;
  if (m === 3) return 30_000;
  return 0;
}
function prizePower535(m: number, s: number): number {
  if (m === 5 && s === 1) return 6_000_000_000;
  if (m === 5) return 10_000_000;
  if (m === 4 && s === 1) return 5_000_000;
  if (m === 4) return 500_000;
  if (m === 3 && s === 1) return 100_000;
  if (m === 3) return 30_000;
  if (s === 1 && m >= 0) return 10_000;
  return 0;
}

interface NormalizedPrizes {
  [name: string]: { prizeValue: number; winnersCount: number };
}

function normalizePrizes(product: ProductName, record: PrizeRecord): NormalizedPrizes {
  const out: NormalizedPrizes = {};
  for (const p of record.prizes) {
    const name = (p.prize_name ?? "").trim();
    out[name] = {
      prizeValue: parseVnd(p.prize_value),
      winnersCount: parseWinners(p.winners_count),
    };
    if (product === "power_535" && CONSOLATION_NAMES.has(name)) {
      out["Giải Khuyến Khích"] = { prizeValue: parseVnd(p.prize_value), winnersCount: parseWinners(p.winners_count) };
    }
  }
  return out;
}

const prizeIndexCache = new Map<string, Record<string, NormalizedPrizes>>();

function getPrizeIndex(product: ProductName, records: PrizeRecord[]): Record<string, NormalizedPrizes> {
  const cached = prizeIndexCache.get(product);
  if (cached) return cached;
  const idx: Record<string, NormalizedPrizes> = {};
  for (const r of records) {
    if (r.id == null) continue;
    const rawId = String(r.id).trim();
    const norm = normalizePrizes(product, r);
    idx[rawId] = norm;
    const val = parseInt(rawId, 10);
    if (!isNaN(val)) {
      idx[String(val)] = norm;
      idx[String(val).padStart(5, "0")] = norm;
    }
  }
  prizeIndexCache.set(product, idx);
  return idx;
}

export function clearPrizeIndex(): void {
  prizeIndexCache.clear();
}

/**
 * Get the actual prize (VND) for a given draw from the crawled prize data,
 * applying the Power 5/35 split rule when applicable.
 */
export function getActualPrizeForDraw(
  product: ProductName,
  records: PrizeRecord[],
  drawId: string | number,
  mainMatch: number,
  specialMatch: number,
): number {
  const fb = () => fallbackPrize(product, mainMatch, specialMatch);
  if (drawId == null) return fb();
  const idx = getPrizeIndex(product, records);
  const drawIdStr = String(drawId).trim();
  let prizes = idx[drawIdStr];
  if (!prizes) {
    const val = parseInt(drawIdStr, 10);
    if (!isNaN(val)) {
      prizes = idx[String(val)] || idx[String(val).padStart(5, "0")];
    }
  }
  if (!prizes) return fb();

  const prizeName = lookupPrizeName(product, mainMatch, specialMatch);
  if (prizeName === null) return fb();

  let tierInfo = prizes[prizeName];
  if (!tierInfo && product === "power_535") {
    for (const alias of CONSOLATION_NAMES) {
      if (prizes[alias]) {
        tierInfo = prizes[alias];
        break;
      }
    }
  }
  if (!tierInfo) return fb();

  const pv = tierInfo.prizeValue;
  const w = tierInfo.winnersCount;

  if (product !== "power_535") return pv;

  // --- power_535: full simulation with 1/3-1/6 split + redistribution ---
  // Độc Đắc match (5 main + 1 special).
  if (mainMatch === 5 && specialMatch === 1) {
    const dd = prizes["Giải Độc Đắc"];
    if (!dd) return fb();
    const ddW = dd.winnersCount;
    const ddV = dd.prizeValue;
    if (ddW === 0) return ddV;
    return Math.trunc((ddV * ddW) / (ddW + 1));
  }

  // Consolation (Khuyến Khích) is always 10K per winner, not part of split.
  if (CONSOLATION_NAMES.has(prizeName)) return 10_000;

  // Lower-tier match.  Detect split event.
  const dd = prizes["Giải Độc Đắc"];
  let isSplit = false;
  let ddV = 0;
  if (dd) {
    ddV = dd.prizeValue;
    const ddW = dd.winnersCount;
    const nhiInfo = prizes["Giải Nhì"];
    const nhiV = nhiInfo?.prizeValue ?? 0;
    isSplit =
      ddV > POWER_535_SPLIT_THRESHOLD &&
      ddW === 0 &&
      nhiV > POWER_535_STANDARD_PV["Giải Nhì"];
  }

  if (!isSplit || !(prizeName in POWER_535_STANDARD_PV)) {
    return pv;
  }

  // Split case.  Build the hypothetical winners_count (with our +1)
  // and apply the redistribution rule.
  const splitTiers = ["Giải Nhất", "Giải Nhì", "Giải Ba", "Giải Tư", "Giải Năm"] as const;
  const tierWSim: Record<string, number> = {};
  for (const t of splitTiers) {
    if (t === prizeName) tierWSim[t] = w + 1;
    else tierWSim[t] = prizes[t]?.winnersCount ?? 0;
  }

  const shares: Record<string, number> = {
    "Giải Nhất": Math.trunc(ddV / 3),
    "Giải Nhì": Math.trunc(ddV / 6),
    "Giải Ba": Math.trunc(ddV / 6),
    "Giải Tư": Math.trunc(ddV / 6),
    "Giải Năm": Math.trunc(ddV / 6),
  };

  const zeroTiers = splitTiers.filter((t) => tierWSim[t] === 0);
  const nonZeroTiers = splitTiers.filter((t) => tierWSim[t] > 0);
  for (const zt of zeroTiers) {
    if (nonZeroTiers.length) {
      const perTier = Math.trunc(shares[zt] / nonZeroTiers.length);
      for (const nzt of nonZeroTiers) shares[nzt] += perTier;
      shares[zt] = 0;
    }
  }

  const standardPv = POWER_535_STANDARD_PV[prizeName];
  const ourShare = shares[prizeName];
  const wSim = tierWSim[prizeName];
  return Math.trunc((wSim * standardPv + ourShare) / wSim);
}
