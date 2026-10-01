// Steiner system-based prediction strategy (port of strategies/steiner.py).
//
// Builds a partial Steiner system S(t, k, v) (t-wise-disjoint k-subsets) over
// the number range and selects ``numberPredict`` numbers by combining the
// top-scoring structural units based on historical co-occurrence.

import type { DrawRow } from "./base";
import { PredictModel as PredictModelClass } from "./base";

type Triple = number[];

function* combinations<T>(arr: T[], k: number): Generator<T[]> {
  const n = arr.length;
  if (k > n || k <= 0) return;
  const idx = Array.from({ length: k }, (_, i) => i);
  while (true) {
    yield idx.map((i) => arr[i]);
    let i = k - 1;
    while (i >= 0 && idx[i] === n - k + i) i--;
    if (i < 0) return;
    idx[i]++;
    for (let j = i + 1; j < k; j++) idx[j] = idx[j - 1] + 1;
  }
}

function combinationsArray<T>(arr: T[], k: number): T[][] {
  return Array.from(combinations(arr, k));
}

function tupleKey(a: number, b: number): [number, number] {
  return a < b ? [a, b] : [b, a];
}

export class SteinerStrategy extends PredictModelClass {
  static DEFAULT_STEINER_SYSTEM: Record<string, [number, number, number]> = {
    power_535: [2, 3, 35],
    power_645: [2, 3, 45],
    power_655: [2, 3, 55],
  };

  lookbackDays: number | null;
  filterConsecutive: boolean;
  filterSameDecade: boolean;
  t: number;
  k: number;
  v: number;

  private blocks: Triple[];
  private pairFreqCache = new Map<string, Map<string, number>>();
  private topTicketsCache = new Map<string, number[][]>();
  private poolBlocksCache = new Map<string, Triple[]>();
  private callCounter = 0;

  constructor(
    df: DrawRow[],
    timePredict = 1,
    minVal = PredictModelClass.POWER_655_MIN_VAL,
    maxVal = PredictModelClass.POWER_655_MAX_VAL,
    options: {
      lookbackDays?: number | null;
      filterConsecutive?: boolean;
      filterSameDecade?: boolean;
      t?: number;
      k?: number;
      v?: number | null;
    } = {},
  ) {
    super(df, timePredict, minVal, maxVal);
    const { lookbackDays = 365, filterConsecutive = true, filterSameDecade = true, t = 2, k = 3, v = null } = options;

    if (t < 1) throw new Error(`Steiner strength t must be >= 1, got ${t}`);
    if (k < t) throw new Error(`Block size k=${k} must be >= t=${t}`);
    const poolSize = this.maxVal - this.minVal + 1;
    if (k > poolSize) throw new Error(`Block size k=${k} is larger than the number range (${poolSize})`);

    this.lookbackDays = lookbackDays;
    this.filterConsecutive = filterConsecutive;
    this.filterSameDecade = filterSameDecade;
    this.t = t;
    this.k = k;
    const effectiveV = v != null && v > 0 ? v : this.maxVal;
    if (effectiveV < k) throw new Error(`Steiner v=${effectiveV} must be >= k=${k}`);
    if (effectiveV < this.minVal) throw new Error(`Steiner v=${effectiveV} must be >= minVal=${this.minVal}`);
    this.v = effectiveV;

    this.blocks = this.buildPartialSteiner();
  }

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------

  static isValidTriple(
    triple: number[],
    filterConsecutive = true,
    filterSameDecade = true,
  ): boolean {
    if (triple.length !== 3) return false;
    const [a, b, c] = [...triple].sort((x, y) => x - y);
    if (filterConsecutive && (b - a === 1 || c - b === 1)) return false;
    if (filterSameDecade && Math.floor(a / 10) === Math.floor(b / 10) && Math.floor(b / 10) === Math.floor(c / 10)) {
      return false;
    }
    return true;
  }

  private isValidBlock(block: number[]): boolean {
    if (this.k === 3 && block.length === 3) {
      return SteinerStrategy.isValidTriple(block, this.filterConsecutive, this.filterSameDecade);
    }
    return new Set(block).size === block.length && block.length === this.k;
  }

  // ------------------------------------------------------------------
  // Steiner system construction
  // ------------------------------------------------------------------

  private buildPartialSteiner(): Triple[] {
    const v = this.v;
    const k = this.k;
    const t = this.t;
    const rng: number[] = [];
    for (let n = this.minVal; n < this.minVal + v; n++) rng.push(n);

    const blocks: Triple[] = [];
    const covered = new Set<string>();

    for (const anchor of combinationsArray(rng, t)) {
      const anchorSet = new Set(anchor);
      const anchorSorted = [...anchor].sort((a, b) => a - b);
      const anchorValSet = anchorSorted.join(",");
      if (covered.has(anchorValSet)) continue;
      const extras: number[] = [];
      for (const n of rng) {
        if (anchorSet.has(n)) continue;
        const blockVals = [...anchorSorted, ...extras, n];
        let conflict = false;
        for (const tup of combinationsArray(blockVals, t)) {
          if (covered.has([...tup].sort((a, b) => a - b).join(","))) {
            conflict = true;
            break;
          }
        }
        if (conflict) continue;
        extras.push(n);
        if (extras.length === k - t) break;
      }
      if (extras.length < k - t) continue;
      const block = [...anchorSorted, ...extras].sort((a, b) => a - b);
      blocks.push(block);
      for (const tup of combinationsArray(block, t)) {
        covered.add([...tup].sort((a, b) => a - b).join(","));
      }
    }
    return blocks;
  }

  // ------------------------------------------------------------------
  // Pair co-occurrence
  // ------------------------------------------------------------------

  private pairFreq(targetDate: string): Map<string, number> {
    const cached = this.pairFreqCache.get(targetDate);
    if (cached) return cached;

    const target = new Date(targetDate).getTime();
    const cutoff =
      this.lookbackDays != null ? target - this.lookbackDays * 86_400_000 : -Infinity;

    const freq = new Map<string, number>();
    for (const row of this.dfSorted) {
      const t = new Date(row.date).getTime();
      if (t >= target) continue;
      if (t < cutoff) continue;
      const nums = [...this.mainNumbers(row.result)].sort((a, b) => a - b);
      for (const [a, b] of combinationsArray(nums, 2) as Array<[number, number]>) {
        const key = tupleKey(a, b).join(",");
        freq.set(key, (freq.get(key) ?? 0) + 1);
      }
    }
    this.pairFreqCache.set(targetDate, freq);
    return freq;
  }

  private static scoreBlock(block: number[], freq: Map<string, number>): number {
    let score = 0;
    const sorted = [...block].sort((a, b) => a - b);
    for (const [a, b] of combinationsArray(sorted, 2) as Array<[number, number]>) {
      score += freq.get(tupleKey(a, b).join(",")) ?? 0;
    }
    return score;
  }

  // ------------------------------------------------------------------
  // Top-K candidate tickets
  // ------------------------------------------------------------------

  private blocksPerTicket(): number {
    if (this.k <= 0) return 1;
    return Math.max(1, Math.ceil(this.numberPredict / this.k));
  }

  private scoredBlocks(targetDate: string): Array<[number, number, number[]]> {
    const freq = this.pairFreq(targetDate);
    let blocks: number[][];
    if (this.filterConsecutive || this.filterSameDecade) {
      blocks = this.blocks.filter((b) => this.isValidBlock(b));
    } else {
      blocks = [...this.blocks];
    }
    const scored = blocks.map((b, idx) => [SteinerStrategy.scoreBlock(b, freq), idx, b] as [number, number, number[]]);
    scored.sort((a, b) => b[0] - a[0] || a[1] - b[1]);
    return scored;
  }

  private topTickets(targetDate: string, k: number): number[][] {
    const key = `${targetDate}|${k}`;
    const cached = this.topTicketsCache.get(key);
    if (cached) return cached;
    const scored = this.scoredBlocks(targetDate);
    if (!scored.length) {
      this.topTicketsCache.set(key, []);
      return [];
    }
    const blocksPerTicket = this.blocksPerTicket();
    const result: number[][] = [];
    const seen = new Set<string>();
    for (let i = 0; i < scored.length; i++) {
      if (result.length >= k) break;
      const b1 = scored[i][2];
      const ticketNums = new Set(b1);
      let unitsLeft = blocksPerTicket - 1;
      for (let j = 0; j < scored.length; j++) {
        if (unitsLeft === 0) break;
        if (j === i) continue;
        const b2 = scored[j][2];
        let overlap = false;
        for (const n of b2) {
          if (ticketNums.has(n)) {
            overlap = true;
            break;
          }
        }
        if (overlap) continue;
        for (const n of b2) ticketNums.add(n);
        unitsLeft--;
      }
      const ticket = [...ticketNums].sort((a, b) => a - b).slice(0, this.numberPredict);
      if (ticket.length !== this.numberPredict) continue;
      const ticketKey = ticket.join(",");
      if (seen.has(ticketKey)) continue;
      seen.add(ticketKey);
      result.push(ticket);
    }
    this.topTicketsCache.set(key, result);
    return result;
  }

  getTopTickets(targetDate: string, k: number): number[][] {
    return this.topTickets(targetDate, k);
  }

  getTopNumbers(targetDate: string, k = 15): number[] {
    const effectiveK = Math.max(k, this.numberPredict);
    const tickets = this.topTickets(targetDate, Math.max(3, Math.ceil((effectiveK + this.k - 1) / this.k)));
    const seen = new Set<number>();
    const result: number[] = [];
    for (const t of tickets) {
      for (const n of t) {
        if (!seen.has(n)) {
          seen.add(n);
          result.push(n);
          if (result.length >= effectiveK) return result;
        }
      }
    }
    for (let n = this.minVal; n < this.minVal + this.v; n++) {
      if (!seen.has(n)) {
        seen.add(n);
        result.push(n);
        if (result.length >= effectiveK) break;
      }
    }
    return result;
  }

  // ------------------------------------------------------------------
  // Constrained Steiner on a custom pool (used by InverseHybridStrategy)
  // ------------------------------------------------------------------

  static buildSteinerOnPool(pool: number[], k = 3, t = 2): number[][] {
    const sortedPool = [...new Set(pool)].sort((a, b) => a - b);
    const n = sortedPool.length;
    if (n < k) return [];
    if (t < 1 || k < t || k > n) return [];
    const blocks: number[][] = [];
    const covered = new Set<string>();
    const indices = Array.from({ length: n }, (_, i) => i);
    for (const anchor of combinationsArray(indices, t)) {
      const anchorSet = new Set(anchor);
      const anchorVals = anchor.map((i) => sortedPool[i]).sort((a, b) => a - b);
      const anchorKey = anchorVals.join(",");
      if (covered.has(anchorKey)) continue;
      const extras: number[] = [];
      for (const ni of indices) {
        if (anchorSet.has(ni)) continue;
        const blockVals = [...anchorVals, ...extras, sortedPool[ni]];
        let conflict = false;
        for (const tup of combinationsArray(blockVals, t)) {
          if (covered.has([...tup].sort((a, b) => a - b).join(","))) {
            conflict = true;
            break;
          }
        }
        if (conflict) continue;
        extras.push(ni);
        if (extras.length === k - t) break;
      }
      if (extras.length < k - t) continue;
      const block = [...anchorVals, ...extras.map((i) => sortedPool[i])].sort((a, b) => a - b);
      blocks.push(block);
      for (const tup of combinationsArray(block, t)) {
        covered.add([...tup].sort((a, b) => a - b).join(","));
      }
    }
    return blocks;
  }

  private buildSteinerOnPoolCached(pool: number[], k = 3, t = 2): number[][] {
    const key = `${[...pool].sort((a, b) => a - b).join(",")}|${k}|${t}`;
    const cached = this.poolBlocksCache.get(key);
    if (cached) return cached;
    const blocks = SteinerStrategy.buildSteinerOnPool(pool, k, t);
    this.poolBlocksCache.set(key, blocks);
    if (this.poolBlocksCache.size > 256) {
      const firstKey = this.poolBlocksCache.keys().next().value;
      if (firstKey !== undefined) this.poolBlocksCache.delete(firstKey);
    }
    return blocks;
  }

  private poolPairFreq(targetDate: string, pool: number[]): Map<string, number> {
    const full = this.pairFreq(targetDate);
    const poolSet = new Set(pool);
    const result = new Map<string, number>();
    for (const [k, v] of full) {
      const [a, b] = k.split(",").map(Number);
      if (poolSet.has(a) && poolSet.has(b)) result.set(k, v);
    }
    return result;
  }

  static decomposeIntoUnits(n: number): number[] {
    if (n < 1) return [];
    const units: number[] = [];
    while (n >= 3) {
      units.push(3);
      n -= 3;
    }
    if (n === 2) units.push(2);
    else if (n === 1) units.push(1);
    return units;
  }

  private bestDisjointUnit(
    used: Set<number>,
    triples: number[][],
    freq: Map<string, number>,
    unitSize: number,
    pool: number[],
  ): Set<number> {
    if (unitSize === 3) {
      let best: number[] | null = null;
      let bestScore = -1;
      for (const t of triples) {
        let overlap = false;
        for (const n of t) {
          if (used.has(n)) {
            overlap = true;
            break;
          }
        }
        if (overlap) continue;
        const s = SteinerStrategy.scoreBlock(t, freq);
        if (s > bestScore) {
          bestScore = s;
          best = t;
        }
      }
      return best ? new Set(best) : new Set();
    }
    if (unitSize === 2) {
      let bestPair: [number, number] | null = null;
      let bestScore = -1;
      for (let i = 0; i < pool.length; i++) {
        const a = pool[i];
        if (used.has(a)) continue;
        for (let j = i + 1; j < pool.length; j++) {
          const b = pool[j];
          if (used.has(b)) continue;
          const s = freq.get(tupleKey(a, b).join(",")) ?? 0;
          if (s > bestScore) {
            bestScore = s;
            bestPair = [a, b];
          }
        }
      }
      return bestPair ? new Set(bestPair) : new Set();
    }
    if (unitSize === 1) {
      if (used.size === 0) {
        let bestN: number | null = null;
        let bestScore = -1;
        for (const n of pool) {
          let s = 0;
          for (const m of pool) {
            if (m === n) continue;
            s += freq.get(tupleKey(n, m).join(",")) ?? 0;
          }
          if (s > bestScore) {
            bestScore = s;
            bestN = n;
          }
        }
        return bestN != null ? new Set([bestN]) : new Set();
      }
      const scores: Record<number, number> = {};
      for (const n of pool) {
        if (used.has(n)) continue;
        let s = 0;
        for (const a of used) s += freq.get(tupleKey(n, a).join(",")) ?? 0;
        scores[n] = s;
      }
      const keys = Object.keys(scores);
      if (!keys.length) return new Set();
      let bestN = Number(keys[0]);
      for (const k of keys) {
        if (scores[Number(k)] > scores[bestN]) bestN = Number(k);
      }
      return new Set([bestN]);
    }
    return new Set();
  }

  private randomSample<T>(arr: T[], k: number): T[] {
    const a = [...arr];
    const out: T[] = [];
    for (let i = 0; i < k && a.length; i++) {
      const idx = Math.floor(Math.random() * a.length);
      out.push(a[idx]);
      a.splice(idx, 1);
    }
    return out;
  }

  predictFromPool(
    targetDate: string,
    pool: number[],
    coverage = 3,
    numberPredict: number | null = null,
  ): number[] {
    const k = numberPredict ?? this.numberPredict;
    const sortedPool = [...new Set(pool)].sort((a, b) => a - b);
    if (sortedPool.length < k) {
      const need = k - sortedPool.length;
      const extra: number[] = [];
      for (let n = this.minVal; n <= this.maxVal && extra.length < need; n++) {
        if (!sortedPool.includes(n)) extra.push(n);
      }
      return [...sortedPool, ...extra].sort((a, b) => a - b).slice(0, k);
    }

    const poolFreq = this.poolPairFreq(targetDate, sortedPool);

    if (this.k === 3) {
      const triples = this.buildSteinerOnPoolCached(sortedPool, 3, this.t);
      if (!triples.length) return sortedPool.slice(0, k);

      if (k <= 2) {
        const unit = this.bestDisjointUnit(new Set(), triples, poolFreq, k, sortedPool);
        const set = new Set(unit);
        if (set.size < k) {
          for (const n of sortedPool) {
            if (!set.has(n)) {
              set.add(n);
              if (set.size >= k) break;
            }
          }
        }
        return [...set].sort((a, b) => a - b).slice(0, k);
      }

      const units = SteinerStrategy.decomposeIntoUnits(k);
      const scoredTriples = triples
        .map((t, idx) => [SteinerStrategy.scoreBlock(t, poolFreq), idx, t] as [number, number, number[]])
        .sort((a, b) => b[0] - a[0] || a[1] - b[1]);

      const steinerTickets: Array<number[]> = [];
      const seen = new Set<string>();
      for (const [, , t1] of scoredTriples) {
        if (steinerTickets.length >= coverage) break;
        const ticketNums = new Set(t1);
        let success = true;
        for (const unitSize of units.slice(1)) {
          const unitSet = this.bestDisjointUnit(ticketNums, triples, poolFreq, unitSize, sortedPool);
          if (unitSet.size === 0) {
            success = false;
            break;
          }
          for (const n of unitSet) ticketNums.add(n);
        }
        if (!success || ticketNums.size !== k) continue;
        const ticket = [...ticketNums].sort((a, b) => a - b);
        const key = ticket.join(",");
        if (seen.has(key)) continue;
        seen.add(key);
        steinerTickets.push(ticket);
      }

      // Top up with random samples.
      const randomTickets: number[][] = [];
      if (steinerTickets.length < coverage) {
        const needed = coverage - steinerTickets.length;
        for (let i = 0; i < needed * 3 && randomTickets.length < needed; i++) {
          const sample =
            sortedPool.length <= k
              ? [...sortedPool].sort((a, b) => a - b)
              : [...this.randomSample(sortedPool, k)].sort((a, b) => a - b);
          const key = sample.join(",");
          if (seen.has(key)) continue;
          seen.add(key);
          randomTickets.push(sample);
        }
        while (randomTickets.length < needed) {
          let fallback = sortedPool.slice(0, k);
          if (seen.has(fallback.join(","))) {
            for (let offset = 1; offset < sortedPool.length; offset++) {
              const cand = sortedPool.slice(offset, offset + k);
              if (cand.length === k && !seen.has(cand.join(","))) {
                fallback = cand;
                break;
              }
            }
          }
          seen.add(fallback.join(","));
          randomTickets.push(fallback);
        }
      }

      const tickets = [...steinerTickets, ...randomTickets];
      if (!tickets.length) return sortedPool.slice(0, k);
      const idx = this.callCounter++;
      return tickets[idx % tickets.length];
    }

    // General-k path.
    const blocks = this.buildSteinerOnPoolCached(sortedPool, this.k, this.t);
    if (!blocks.length) return sortedPool.slice(0, k);
    const scored = blocks
      .map((b, idx) => [SteinerStrategy.scoreBlock(b, poolFreq), idx, b] as [number, number, number[]])
      .sort((a, b) => b[0] - a[0] || a[1] - b[1]);
    const blocksPerTicket = Math.max(1, Math.ceil(k / this.k));
    const steinerTickets: number[][] = [];
    const seen = new Set<string>();
    for (const [, , b1] of scored) {
      if (steinerTickets.length >= coverage) break;
      const ticketNums = new Set(b1);
      let unitsLeft = blocksPerTicket - 1;
      for (const [, , b2] of scored) {
        if (unitsLeft === 0) break;
        let overlap = false;
        for (const n of b2) {
          if (ticketNums.has(n)) {
            overlap = true;
            break;
          }
        }
        if (overlap) continue;
        for (const n of b2) ticketNums.add(n);
        unitsLeft--;
      }
      const ticket = [...ticketNums].sort((a, b) => a - b).slice(0, k);
      if (ticket.length !== k) continue;
      const key = ticket.join(",");
      if (seen.has(key)) continue;
      seen.add(key);
      steinerTickets.push(ticket);
    }
    const randomTickets: number[][] = [];
    if (steinerTickets.length < coverage) {
      const needed = coverage - steinerTickets.length;
      for (let i = 0; i < needed * 3 && randomTickets.length < needed; i++) {
        const sample =
          sortedPool.length <= k
            ? [...sortedPool].sort((a, b) => a - b)
            : [...this.randomSample(sortedPool, k)].sort((a, b) => a - b);
        const key = sample.join(",");
        if (seen.has(key)) continue;
        seen.add(key);
        randomTickets.push(sample);
      }
      while (randomTickets.length < needed) {
        let fallback = sortedPool.slice(0, k);
        if (seen.has(fallback.join(","))) {
          for (let offset = 1; offset < sortedPool.length; offset++) {
            const cand = sortedPool.slice(offset, offset + k);
            if (cand.length === k && !seen.has(cand.join(","))) {
              fallback = cand;
              break;
            }
          }
        }
        seen.add(fallback.join(","));
        randomTickets.push(fallback);
      }
    }
    const tickets = [...steinerTickets, ...randomTickets];
    if (!tickets.length) return sortedPool.slice(0, k);
    const idx = this.callCounter++;
    return tickets[idx % tickets.length];
  }

  // ------------------------------------------------------------------
  // PredictModel interface
  // ------------------------------------------------------------------

  filterPool(targetDate: string, pool: number[], k: number, coverage = 1): number[] {
    if (k >= pool.length) return [...new Set(pool)].sort((a, b) => a - b);
    return this.predictFromPool(targetDate, [...pool], Math.max(1, coverage), k).sort((a, b) => a - b);
  }

  predict(date: string, candidatePool?: number[] | null): number[] {
    if (candidatePool != null) {
      return this.predictFromPool(date, [...candidatePool], Math.max(this.timePredict, 1));
    }
    const tickets = this.topTickets(date, Math.max(this.timePredict, 1));
    if (!tickets.length) {
      const nums: number[] = [];
      for (const blk of this.blocks) {
        for (const n of blk) {
          if (!nums.includes(n)) nums.push(n);
          if (nums.length >= this.numberPredict) break;
        }
        if (nums.length >= this.numberPredict) break;
      }
      let n = this.minVal;
      while (nums.length < this.numberPredict && n <= this.maxVal) {
        if (!nums.includes(n)) nums.push(n);
        n++;
      }
      return nums.sort((a, b) => a - b).slice(0, this.numberPredict);
    }
    const idx = this.callCounter++;
    return tickets[idx % tickets.length];
  }
}
