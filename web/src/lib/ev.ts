// EV (Expected Value) estimation for Power 5/35.
//
// Domain facts (verified from data/power535*.jsonl and Vietlott rules):
//   - 5 main numbers from 1-35.
//   - 1 special number from 1-12 (12 values, NOT 0-9).
//   - Ticket price: 10,000 VND.
//   - Jackpot is funded at 55% of the draw's actual revenue.
//   - Jackpot base after a winner: 6,000,000,000 VND.
//   - Tier 1-5 prizes (Nhất→Năm) are fixed amounts; only Jackpot varies.
//   - When Jackpot > 12B and 0 winners in a draw, the rule in prizes.ts kicks
//     in (1/3 → Nhất, 1/6 → each of Nhì/Ba/Tư/Năm).  The "tickets sold" math
//     here ignores that redistribution — EV is a per-ticket expected value
//     using the *standard* prize table, plus an explicit Jackpot share.
//
// EV formula per ticket:
//   EV = Σ P(win_tier_i) × E[payout_tier_i] − ticket_price
//
// P(win_tier_i) is combinatorial (independent of history) because the draw
// is uniform over all C(35,5) × 12 = 3,895,584 tickets.  E[payout_tier_i] is
// projected from the previous draw(s)' prize structure.

import type { Draw, PrizeRecord } from "./types";

// ---------- constants (Power 5/35) ----------

export const POWER_535_JACKPOT_BASE = 6_000_000_000;
export const POWER_535_SPLIT_THRESHOLD = 12_000_000_000;
export const POWER_535_SHARE_JACKPOT = 0.55;
export const POWER_535_TICKET_PRICE = 10_000;
export const POWER_535_NUM_SPECIALS = 12;
export const POWER_535_NUM_MAINS = 35;
export const POWER_535_NUM_PICKS = 5;

const C5 = 324_632; // C(35, 5)
const TOTAL_TICKETS = C5 * POWER_535_NUM_SPECIALS; // 3,895,584

export const POWER_535_TIER_PROBS: Readonly<Record<string, number>> = Object.freeze({
  // P(5+1) — Jackpot
  jackpot: 1 / TOTAL_TICKETS,
  // P(5+0) — Tier Nhất
  nhat: 11 / TOTAL_TICKETS,
  // P(4+1) — Tier Nhì
  nhi: (5 * 30) / TOTAL_TICKETS,
  // P(4+0) — Tier Ba
  ba: (5 * 30 * 11) / TOTAL_TICKETS,
  // P(3+1) — Tier Tư
  tu: (10 * 435) / TOTAL_TICKETS,
  // P(3+0) — Tier Năm
  nam: (10 * 435 * 11) / TOTAL_TICKETS,
  // P(2+1) ∪ P(1+1) — Khuyến Khích (consolation)
  khuyen_khich:
    ((10 * 4_060 + 5 * 27_405) * 1) / TOTAL_TICKETS,
});

export const POWER_535_FIXED_TIERS: Readonly<Record<string, number>> = Object.freeze({
  nhat: 10_000_000,
  nhi: 5_000_000,
  ba: 500_000,
  tu: 100_000,
  nam: 30_000,
  khuyen_khich: 10_000,
});

/** Map of tier key → display name as stored in prize data. */
const TIER_DISPLAY: Readonly<Record<string, string>> = Object.freeze({
  nhat: "Giải Nhất",
  nhi: "Giải Nhì",
  ba: "Giải Ba",
  tu: "Giải Tư",
  nam: "Giải Năm",
  khuyen_khich: "Giải Khuyến Khích",
});

// ---------- helpers ----------

/** Parse Vietnamese-formatted number string ("2.921" → 2921) into integer. */
export function parseVnNumber(value: unknown): number {
  if (typeof value === "number") return Math.trunc(value);
  if (typeof value === "string") {
    const cleaned = value.replace(/[.,\s]/g, "");
    if (!cleaned) return 0;
    const n = Number(cleaned);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
  }
  return 0;
}

export interface DrawWithPrizes extends Draw {
  prizes: { prize_name: string; prize_value: string; winners_count: string }[];
}

/** Pull a single tier's value & winners, with case/whitespace tolerance. */
export function getTier(
  draw: DrawWithPrizes,
  prizeName: string,
): { prizeValue: number; winnersCount: number } | null {
  const tier = draw.prizes.find(
    (p) => p.prize_name?.trim() === prizeName,
  );
  if (!tier) return null;
  return {
    prizeValue: parseVnNumber(tier.prize_value),
    winnersCount: parseVnNumber(tier.winners_count),
  };
}

// ---------- back-calc of revenue & tickets sold for an observed draw ----------

export interface DrawRevenueEstimate {
  jackpotValue: number;
  jackpotWinners: number;
  hasJackpotWinner: boolean;
  carryover: number; // J entering this draw (base or full prev J)
  freshContribution: number; // 0.55 × revenue
  revenue: number;
  tickets: number;
}

export function estimateDrawRevenue(
  draw: DrawWithPrizes,
  prevDraw: DrawWithPrizes | null,
  jackpotBase: number = POWER_535_JACKPOT_BASE,
): DrawRevenueEstimate {
  const dd = getTier(draw, "Giải Độc Đắc");
  const jackpotValue = dd?.prizeValue ?? 0;
  const jackpotWinners = dd?.winnersCount ?? 0;
  const hasJackpotWinner = jackpotWinners > 0;

  let carryover = jackpotBase;
  if (!hasJackpotWinner && prevDraw) {
    const prevDd = getTier(prevDraw, "Giải Độc Đắc");
    carryover = prevDd?.prizeValue ?? jackpotBase;
  }

  const freshContribution = Math.max(0, jackpotValue - carryover);
  const revenue = freshContribution / POWER_535_SHARE_JACKPOT;
  const tickets = Math.max(0, revenue / POWER_535_TICKET_PRICE);

  return {
    jackpotValue,
    jackpotWinners,
    hasJackpotWinner,
    carryover,
    freshContribution,
    revenue,
    tickets,
  };
}

// ---------- projection of next-draw Jackpot & ticket volume ----------

/** Mean winners per tier across the recent draws (used for split-mode EV). */
export interface TierWinnerExpectations {
  jackpot: number;
  nhat: number;
  nhi: number;
  ba: number;
  tu: number;
  nam: number;
  khuyen_khich: number;
}

const ZERO_WINNERS: TierWinnerExpectations = {
  jackpot: 0,
  nhat: 0,
  nhi: 0,
  ba: 0,
  tu: 0,
  nam: 0,
  khuyen_khich: 0,
};

export interface NextDrawProjection {
  /** Expected Jackpot value for the next draw, in VND. */
  expectedNextJackpot: number;
  /** Expected revenue for the next draw, in VND. */
  expectedRevenue: number;
  /** Expected number of tickets sold in the next draw. */
  expectedTickets: number;
  /** Average of estimated tickets across the most recent N observed draws. */
  avgTicketsLastN: number;
  /** Sample size (number of draws used). */
  sampleSize: number;
  /** Confidence based on sample size + J_last magnitude. */
  confidence: "low" | "medium" | "high";
  /** Average of observed Jackpot-winner count for the last N draws. */
  avgJackpotWinnersLastN: number;
  /** Mean winners per tier over the recent N draws. */
  expectedWinners: TierWinnerExpectations;
  /**
   * True when the projected next Jackpot is large enough to trigger the split
   * rule AND the recent Jackpot-winning rate is ~0.  When true, lower-tier
   * payouts (Nhất→Năm) are computed via the 1/3 / 1/6 redistribution instead
   * of the fixed standard values.
   */
  splitMode: boolean;
}

function meanWinners(slice: DrawWithPrizes[]): TierWinnerExpectations {
  if (slice.length === 0) return { ...ZERO_WINNERS };
  const sum: TierWinnerExpectations = { ...ZERO_WINNERS };
  for (const d of slice) {
    sum.jackpot += getTier(d, "Giải Độc Đắc")?.winnersCount ?? 0;
    sum.nhat += getTier(d, "Giải Nhất")?.winnersCount ?? 0;
    sum.nhi += getTier(d, "Giải Nhì")?.winnersCount ?? 0;
    sum.ba += getTier(d, "Giải Ba")?.winnersCount ?? 0;
    sum.tu += getTier(d, "Giải Tư")?.winnersCount ?? 0;
    sum.nam += getTier(d, "Giải Năm")?.winnersCount ?? 0;
    sum.khuyen_khich += getTier(d, "Giải Khuyến Khích")?.winnersCount ?? 0;
  }
  const n = slice.length;
  return {
    jackpot: sum.jackpot / n,
    nhat: sum.nhat / n,
    nhi: sum.nhi / n,
    ba: sum.ba / n,
    tu: sum.tu / n,
    nam: sum.nam / n,
    khuyen_khich: sum.khuyen_khich / n,
  };
}

export function projectNextDraw(
  recentDraws: DrawWithPrizes[],
  jackpotBase: number = POWER_535_JACKPOT_BASE,
  n: number = 10,
): NextDrawProjection {
  const slice = recentDraws.slice(0, n);
  if (slice.length === 0) {
    return {
      expectedNextJackpot: jackpotBase,
      expectedRevenue: 0,
      expectedTickets: 0,
      avgTicketsLastN: 0,
      sampleSize: 0,
      confidence: "low",
      avgJackpotWinnersLastN: 0,
      expectedWinners: { ...ZERO_WINNERS },
      splitMode: false,
    };
  }

  // Back-calc each draw in the slice.
  const estimates: DrawRevenueEstimate[] = [];
  for (let i = 0; i < slice.length; i++) {
    estimates.push(estimateDrawRevenue(slice[i], slice[i + 1] ?? null, jackpotBase));
  }

  const avgTickets = estimates.reduce((s, e) => s + e.tickets, 0) / estimates.length;
  const avgRevenue = estimates.reduce((s, e) => s + e.revenue, 0) / estimates.length;
  const avgJackpotWinners =
    estimates.reduce((s, e) => s + e.jackpotWinners, 0) / estimates.length;
  const expectedWinners = meanWinners(slice);

  // Project next Jackpot.  Two cases:
  //   1) Last draw had a Jackpot winner → next starts at J_base + 0.55 × E[Rev]
  //   2) Last draw had no Jackpot winner → next = J_last + 0.55 × E[Rev]
  const last = slice[0];
  const lastDd = getTier(last, "Giải Độc Đắc");
  const lastJ = lastDd?.prizeValue ?? jackpotBase;
  const lastHasWinner = (lastDd?.winnersCount ?? 0) > 0;
  const baseForNext = lastHasWinner ? jackpotBase : lastJ;
  const expectedNextJackpot = baseForNext + POWER_535_SHARE_JACKPOT * avgRevenue;

  // Split mode: Jackpot > 12B AND no winners expected (so 0 in projected draw).
  // This is the condition that triggers the 1/3 + 1/6 redistribution.
  const splitMode =
    expectedNextJackpot > POWER_535_SPLIT_THRESHOLD && avgJackpotWinners < 0.5;

  const confidence: NextDrawProjection["confidence"] =
    slice.length >= 8 && avgRevenue > 0 ? "high" : slice.length >= 3 ? "medium" : "low";

  return {
    expectedNextJackpot: Math.round(expectedNextJackpot),
    expectedRevenue: Math.round(avgRevenue),
    expectedTickets: Math.round(avgTickets),
    avgTicketsLastN: Math.round(avgTickets),
    sampleSize: slice.length,
    confidence,
    avgJackpotWinnersLastN: Math.round(avgJackpotWinners * 100) / 100,
    expectedWinners,
    splitMode,
  };
}

// ---------- per-ticket EV ----------

export interface TierEvRow {
  tier: string;
  displayName: string;
  probability: number;
  expectedPayout: number;
  /** p × payout − allocated ticket cost. */
  ev: number;
  /** True if this tier's payout was computed using the split rule. */
  splitAdjusted: boolean;
  /** Mean number of OTHER winners expected in this tier (used in split mode). */
  expectedOtherWinners: number;
}

export interface TicketEv {
  evPerTicket: number; // Σ p × payout − ticket_price
  breakdown: TierEvRow[];
  projection: NextDrawProjection;
  /** Total EV across N tickets (TPD × topN). */
  totalEv: number;
  numTickets: number;
}

/**
 * Compute the expected payout for a single lower-tier win (Nhất→Năm) under
 * the Power 5/35 split rule.  Mirrors the logic in web/src/lib/prizes.ts
 * (and src/vietlott/config/prizes.py).
 *
 *   payout = standardPv + (1/6 × J) / (E[w] + 1)
 *
 * The `+ 1` accounts for our hypothetical win; if E[w] = 0 (no other winners
 * expected) and we win, the per-winner payout simplifies to standardPv + 1/6 J.
 *
 * If our tier is the only one with winners (other 4 tiers all 0), then the
 * redistribution collects all 5 shares (1/3 + 4×1/6 = J) and pushes them onto
 * us.  The above formula already covers this: shares[our_tier] = J/6 + 4×J/6
 * = 5J/6, and dividing by wSim=1 yields 5J/6.
 */
function splitPayoutForTier(
  tier: keyof typeof POWER_535_FIXED_TIERS,
  jackpotNext: number,
  expectedOtherWinners: number,
): number {
  const standardPv = POWER_535_FIXED_TIERS[tier];
  const tierShare = jackpotNext / 6;
  const wSim = expectedOtherWinners + 1;
  // The "1/3" share is for Nhất, not Nhì/Ba/Tư/Năm.  Add it as a base bonus
  // for Nhất when split is active.
  const baseBonus = tier === "nhat" ? jackpotNext / 3 : 0;
  return standardPv + (tierShare + baseBonus) / wSim;
}

export function computeEv(
  recentDraws: DrawWithPrizes[],
  numTickets: number,
  jackpotBase: number = POWER_535_JACKPOT_BASE,
  /**
   * Tier-payout model. Defaults to "fixed" (the standard prize table for
   * a non-split draw).  Pass "historical_mean" to use the empirical mean
   * per-tier payout from the supplied data, which captures the long-term
   * average EV across both split and non-split draws (~7.9% of historical
   * 5/35 draws are split events with elevated lower-tier payouts).
   */
  tierMode: "fixed" | "historical_mean" = "fixed",
): TicketEv {
  const projection = projectNextDraw(recentDraws, jackpotBase, 10);
  const { expectedNextJackpot, expectedWinners, splitMode } = projection;
  const jackW = expectedWinners.jackpot;

  // Empirical mean per-tier payout (across recent draws, all split modes).
  // Used only when tierMode === "historical_mean".
  const meanPayouts: Record<string, number> = {};
  if (tierMode === "historical_mean") {
    for (const t of ["nhat", "nhi", "ba", "tu", "nam", "khuyen_khich"] as const) {
      const tierName = TIER_DISPLAY[t];
      const sum = recentDraws.reduce((s, d) => s + (getTier(d, tierName)?.prizeValue ?? 0), 0);
      meanPayouts[t] = recentDraws.length > 0 ? sum / recentDraws.length : 0;
    }
  }

  // Jackpot tier: we add 1 to the existing winner count to get our share.
  const jackpotPayout = expectedNextJackpot / Math.max(1, jackW + 1);

  // Lower tiers: split-adjusted if splitMode, else fixed (or historical mean).
  const lowerTiers: Array<keyof typeof POWER_535_FIXED_TIERS> = [
    "nhat",
    "nhi",
    "ba",
    "tu",
    "nam",
  ];
  const lowerPayouts: Record<string, { payout: number; splitAdjusted: boolean; w: number }> = {};
  for (const t of lowerTiers) {
    const w = (expectedWinners as unknown as Record<string, number>)[t] ?? 0;
    if (splitMode) {
      lowerPayouts[t] = { payout: splitPayoutForTier(t, expectedNextJackpot, w), splitAdjusted: true, w };
    } else if (tierMode === "historical_mean" && meanPayouts[t] !== undefined) {
      lowerPayouts[t] = { payout: meanPayouts[t], splitAdjusted: false, w };
    } else {
      lowerPayouts[t] = { payout: POWER_535_FIXED_TIERS[t], splitAdjusted: false, w };
    }
  }

  const tiers: { key: string; display: string; payout: number; p: number; splitAdjusted: boolean; w: number }[] = [
    {
      key: "jackpot",
      display: "Giải Độc Đắc",
      payout: jackpotPayout,
      p: POWER_535_TIER_PROBS.jackpot,
      splitAdjusted: false,
      w: jackW,
    },
    {
      key: "nhat",
      display: "Giải Nhất",
      payout: lowerPayouts.nhat.payout,
      p: POWER_535_TIER_PROBS.nhat,
      splitAdjusted: lowerPayouts.nhat.splitAdjusted,
      w: lowerPayouts.nhat.w,
    },
    {
      key: "nhi",
      display: "Giải Nhì",
      payout: lowerPayouts.nhi.payout,
      p: POWER_535_TIER_PROBS.nhi,
      splitAdjusted: lowerPayouts.nhi.splitAdjusted,
      w: lowerPayouts.nhi.w,
    },
    {
      key: "ba",
      display: "Giải Ba",
      payout: lowerPayouts.ba.payout,
      p: POWER_535_TIER_PROBS.ba,
      splitAdjusted: lowerPayouts.ba.splitAdjusted,
      w: lowerPayouts.ba.w,
    },
    {
      key: "tu",
      display: "Giải Tư",
      payout: lowerPayouts.tu.payout,
      p: POWER_535_TIER_PROBS.tu,
      splitAdjusted: lowerPayouts.tu.splitAdjusted,
      w: lowerPayouts.tu.w,
    },
    {
      key: "nam",
      display: "Giải Năm",
      payout: lowerPayouts.nam.payout,
      p: POWER_535_TIER_PROBS.nam,
      splitAdjusted: lowerPayouts.nam.splitAdjusted,
      w: lowerPayouts.nam.w,
    },
    {
      key: "khuyen_khich",
      display: "Giải Khuyến Khích",
      payout: POWER_535_FIXED_TIERS.khuyen_khich,
      p: POWER_535_TIER_PROBS.khuyen_khich,
      splitAdjusted: false,
      w: expectedWinners.khuyen_khich,
    },
  ];

  const breakdown: TierEvRow[] = tiers.map((t) => {
    const ev = t.p * t.payout;
    return {
      tier: t.key,
      displayName: t.display,
      probability: t.p,
      expectedPayout: Math.round(t.payout),
      ev,
      splitAdjusted: t.splitAdjusted,
      expectedOtherWinners: Math.round(t.w * 100) / 100,
    };
  });

  const evPerTicket =
    breakdown.reduce((s, b) => s + b.ev, 0) - POWER_535_TICKET_PRICE;
  const totalEv = evPerTicket * numTickets;

  return {
    evPerTicket,
    breakdown,
    projection,
    totalEv,
    numTickets,
  };
}

// ---------- convenience: turn PrizeRecord[] into DrawWithPrizes[] ----------

/** Merge a sorted (newest-first) PrizeRecord[] onto a Draw[] by draw id. */
export function attachPrizes(draws: Draw[], prizes: PrizeRecord[]): DrawWithPrizes[] {
  const byId = new Map(prizes.map((p) => [p.id, p]));
  const out: DrawWithPrizes[] = [];
  for (const d of draws) {
    const p = byId.get(d.id);
    if (!p) continue;
    out.push({ ...d, prizes: p.prizes });
  }
  return out;
}
