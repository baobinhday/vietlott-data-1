// Frequency-based prediction strategy (port of strategies/frequency.py).
// HotNumbersStrategy = favour frequent, ColdNumbersStrategy = favour rare.

import type { DrawRow } from "./base";
import { PredictModel } from "./base";

export interface FrequencyOptions {
  lookbackDays?: number;
  strategyType?: "hot" | "cold" | "balanced";
  selectionWeight?: number;
}

export class FrequencyStrategy extends PredictModel {
  lookbackDays: number;
  strategyType: "hot" | "cold" | "balanced";
  selectionWeight: number;
  private frequencyCache = new Map<string, Record<number, number>>();

  constructor(
    df: DrawRow[],
    timePredict = 1,
    minVal = PredictModel.POWER_655_MIN_VAL,
    maxVal = PredictModel.POWER_655_MAX_VAL,
    options: FrequencyOptions = {},
  ) {
    super(df, timePredict, minVal, maxVal);
    this.lookbackDays = options.lookbackDays ?? 365;
    this.strategyType = options.strategyType ?? "hot";
    this.selectionWeight = options.selectionWeight ?? 0.8;
  }

  private getFrequencyData(targetDate: string): Record<number, number> {
    const cached = this.frequencyCache.get(targetDate);
    if (cached) return cached;
    const target = new Date(targetDate).getTime();
    const start = target - this.lookbackDays * 86_400_000;
    const counts = new Map<number, number>();
    for (let n = this.minVal; n <= this.maxVal; n++) counts.set(n, 0);
    for (const row of this.dfSorted) {
      const t = new Date(row.date).getTime();
      if (t >= target) continue;
      if (t < start) continue;
      for (const n of this.mainNumbers(row.result)) {
        counts.set(n, (counts.get(n) ?? 0) + 1);
      }
    }
    const result: Record<number, number> = {};
    for (const [k, v] of counts) result[k] = v;
    this.frequencyCache.set(targetDate, result);
    return result;
  }

  private createWeightedPool(freq: Record<number, number>, candidatePool?: number[] | null): number[] {
    let items = Object.entries(freq).map(([n, f]) => [Number(n), f] as [number, number]);
    if (this.strategyType === "hot") {
      items.sort((a, b) => b[1] - a[1] || a[0] - b[0]);
    } else if (this.strategyType === "cold") {
      items.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
    } else {
      // balanced: shuffle
      for (let i = items.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [items[i], items[j]] = [items[j], items[i]];
      }
    }
    if (candidatePool != null) {
      const set = new Set(candidatePool);
      items = items.filter(([n]) => set.has(n));
    }
    const maxFreq = Math.max(1, ...Object.values(freq));
    const weighted: number[] = [];
    for (const [n, f] of items) {
      let weight: number;
      if (this.strategyType === "hot") weight = Math.max(1, f);
      else if (this.strategyType === "cold") weight = Math.max(1, maxFreq - f + 1);
      else weight = 1;
      for (let i = 0; i < weight; i++) weighted.push(n);
    }
    return weighted;
  }

  predict(targetDate: string, candidatePool?: number[] | null): number[] {
    const freq = this.getFrequencyData(targetDate);
    const predicted: number[] = [];
    const frequencyCount = Math.max(0, Math.trunc(this.numberPredict * this.selectionWeight));
    const randomCount = this.numberPredict - frequencyCount;
    if (frequencyCount > 0) {
      const pool = this.createWeightedPool(freq, candidatePool);
      while (predicted.length < frequencyCount && pool.length) {
        const idx = Math.floor(Math.random() * pool.length);
        const chosen = pool[idx];
        if (!predicted.includes(chosen)) predicted.push(chosen);
        // Remove all instances
        for (let i = pool.length - 1; i >= 0; i--) {
          if (pool[i] === chosen) pool.splice(i, 1);
        }
      }
    }
    if (randomCount > 0) {
      const all =
        candidatePool != null
          ? [...candidatePool]
          : Array.from({ length: this.maxVal - this.minVal + 1 }, (_, i) => this.minVal + i);
      const available = all.filter((n) => !predicted.includes(n));
      if (available.length >= randomCount) {
        const sample: number[] = [];
        const tmp = [...available];
        for (let i = 0; i < randomCount; i++) {
          const idx = Math.floor(Math.random() * tmp.length);
          sample.push(tmp[idx]);
          tmp.splice(idx, 1);
        }
        predicted.push(...sample);
      } else {
        predicted.push(...available);
      }
    }
    return predicted.sort((a, b) => a - b);
  }

  /**
   * Propose the ``k`` numbers ranked by frequency (hot or cold).
   * Returned in ascending numeric order for determinism.
   */
  proposeTopNumbers(targetDate: string, k: number): number[] {
    const freq = this.getFrequencyData(targetDate);
    const items = Object.entries(freq).map(([n, f]) => [Number(n), f] as [number, number]);
    if (this.strategyType === "cold") {
      items.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
    } else {
      items.sort((a, b) => b[1] - a[1] || a[0] - b[0]);
    }
    return items.slice(0, k).map(([n]) => n).sort((a, b) => a - b);
  }
}

export class HotNumbersStrategy extends FrequencyStrategy {
  constructor(df: DrawRow[], timePredict = 1, minVal?: number, maxVal?: number, options: FrequencyOptions = {}) {
    super(df, timePredict, minVal, maxVal, { ...options, strategyType: "hot" });
  }
}

export class ColdNumbersStrategy extends FrequencyStrategy {
  constructor(df: DrawRow[], timePredict = 1, minVal?: number, maxVal?: number, options: FrequencyOptions = {}) {
    super(df, timePredict, minVal, maxVal, { ...options, strategyType: "cold" });
  }
}
