// Specials picker (port of _apply_frequency_specials in render_prediction_base.py).
//
// Replaces ``strategy.predictSpecial`` with a top-N frequency picker (per-draw)
// over historical specials in a sliding window.  Supports five modes:
//   * hot                  — most-frequent specials
//   * cold                 — least-frequent specials
//   * long_absence         — specials unseen for the longest time
//   * markov_steiner       — Markov proposed top 8 → Steiner filtered to topN
//   * intersection_la_mc   — intersection of Top-8 LongAbsence and Top-8 Markov
//
// Only meaningful when the product has ``specialPickRequired = true`` (e.g. Power 5/35).

import type { PredictModel } from "./base";
import { SteinerStrategy } from "./steiner";

export type SpecialsMode = "hot" | "cold" | "long_absence" | "markov_steiner" | "intersection_la_mc";

export interface SpecialsOptions {
  topN: number;
  lookbackDraws: number;
  offsetDraws: number;
  mode: SpecialsMode;
}

export function applyFrequencySpecials(strategy: PredictModel, options: SpecialsOptions): void {
  const { topN, lookbackDraws, offsetDraws, mode } = options;
  const cache = new Map<string, number[]>();

  // We capture the strategy's df/result data at the time of the override.  The
  // data is static for a backtest run so the closure is safe.
  const df = strategy.df;
  const specialPosition = strategy.specialPosition;
  const specialMin = strategy.specialMin;
  const specialMax = strategy.specialMax;

  function topFrequencySpecials(targetDate: string): number[] {
    const cached = cache.get(targetDate);
    if (cached) return cached;

    // Filter prior draws (strictly before targetDate)
    const prior = df.filter((row) => row.date < targetDate);
    const totalPrior = prior.length;

    const endIdx = Math.max(0, totalPrior - offsetDraws);
    const startIdx = Math.max(0, endIdx - lookbackDraws);
    const window = prior.slice(startIdx, endIdx);

    // Fallback when there's no history.
    const fallback = (): number[] => {
      const out: number[] = [];
      for (let s = specialMin; s <= specialMax && out.length < topN; s++) out.push(s);
      cache.set(targetDate, out);
      return out;
    };

    if (!window.length) return fallback();

    const specials: number[] = [];
    for (const row of window) {
      if (row.result.length > specialPosition) {
        specials.push(Number(row.result[specialPosition]));
      }
    }
    if (!specials.length) return fallback();

    const allSpecials: number[] = [];
    for (let s = specialMin; s <= specialMax; s++) allSpecials.push(s);
    const counts = new Map<number, number>();
    for (const s of allSpecials) counts.set(s, 0);
    for (const s of specials) counts.set(s, (counts.get(s) ?? 0) + 1);

    if (mode === "cold") {
      const ranked = [...counts.entries()].sort((a, b) => a[1] - b[1] || a[0] - b[0]);
      const chosen = ranked.slice(0, topN).map(([n]) => n).sort((a, b) => a - b);
      cache.set(targetDate, chosen);
      return chosen;
    }
    if (mode === "long_absence") {
      const lastSeenIdx = new Map<number, number>();
      window.forEach((row, idx) => {
        if (row.result.length > specialPosition) {
          lastSeenIdx.set(Number(row.result[specialPosition]), idx);
        }
      });
      const absenceScores = new Map<number, number>();
      for (const s of allSpecials) {
        const last = lastSeenIdx.get(s);
        absenceScores.set(s, last == null ? totalPrior + 1 : totalPrior - last);
      }
      const ranked = [...absenceScores.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
      const chosen = ranked.slice(0, topN).map(([n]) => n).sort((a, b) => a - b);
      cache.set(targetDate, chosen);
      return chosen;
    }
    if (mode === "markov_steiner") {
      let p8: number[] = [...allSpecials];
      if (specials.length >= 2) {
        const trans = new Map<number, Map<number, number>>();
        for (let i = 0; i < specials.length - 1; i++) {
          const prev = specials[i];
          const curr = specials[i + 1];
          if (!trans.has(prev)) trans.set(prev, new Map());
          const inner = trans.get(prev)!;
          inner.set(curr, (inner.get(curr) ?? 0) + 1);
        }
        const lastSp = specials[specials.length - 1];
        const nextCounts = trans.get(lastSp) ?? new Map();
        const scores = new Map<number, number>();
        for (const s of allSpecials) scores.set(s, nextCounts.get(s) ?? 0);
        const rankedMc = [...scores.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
        p8 = rankedMc.slice(0, 8).map(([n]) => n);
      }
      // Steiner filter.
      const stModel = new SteinerStrategy(df, 1, specialMin, specialMax, {
        lookbackDays: null,
        filterConsecutive: false,
        filterSameDecade: false,
      });
      const filterMethod = (stModel as unknown as { filterPool?: (d: string, pool: number[], k: number, c?: number) => number[] }).filterPool;
      let chosen: number[];
      if (typeof filterMethod === "function") {
        chosen = filterMethod.call(stModel, targetDate, p8, topN, 1).sort((a, b) => a - b);
      } else {
        chosen = [...p8].sort((a, b) => a - b).slice(0, topN);
      }
      cache.set(targetDate, chosen);
      return chosen;
    }
    if (mode === "intersection_la_mc") {
      // LongAbsence top 8
      const lastSeenIdx = new Map<number, number>();
      window.forEach((row, idx) => {
        if (row.result.length > specialPosition) {
          lastSeenIdx.set(Number(row.result[specialPosition]), idx);
        }
      });
      const absenceScores = new Map<number, number>();
      for (const s of allSpecials) {
        const last = lastSeenIdx.get(s);
        absenceScores.set(s, last == null ? totalPrior + 1 : totalPrior - last);
      }
      const top8La = new Set(
        [...absenceScores.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]).slice(0, 8).map(([n]) => n),
      );
      // Markov top 8
      let top8Mc: Set<number>;
      if (specials.length >= 2) {
        const trans = new Map<number, Map<number, number>>();
        for (let i = 0; i < specials.length - 1; i++) {
          const prev = specials[i];
          const curr = specials[i + 1];
          if (!trans.has(prev)) trans.set(prev, new Map());
          const inner = trans.get(prev)!;
          inner.set(curr, (inner.get(curr) ?? 0) + 1);
        }
        const lastSp = specials[specials.length - 1];
        const nextCounts = trans.get(lastSp) ?? new Map();
        const scores = new Map<number, number>();
        for (const s of allSpecials) scores.set(s, nextCounts.get(s) ?? 0);
        top8Mc = new Set(
          [...scores.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]).slice(0, 8).map(([n]) => n),
        );
      } else {
        top8Mc = new Set(allSpecials);
      }
      let inter = [...top8La].filter((s) => top8Mc.has(s)).sort((a, b) => a - b).slice(0, topN);
      if (!inter.length) inter = [...top8La].sort((a, b) => a - b).slice(0, topN);
      cache.set(targetDate, inter);
      return inter;
    }
    // hot
    const ranked = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
    const chosen = ranked.slice(0, topN).map(([n]) => n).sort((a, b) => a - b);
    cache.set(targetDate, chosen);
    return chosen;
  }

  (strategy as unknown as { predictSpecial: (d: string, pool?: number[] | null) => number[] }).predictSpecial = (
    targetDate: string,
  ) => topFrequencySpecials(targetDate);
}
