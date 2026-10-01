import { PredictModel } from "./base";
import type { DrawRow } from "./base";
import { SteinerStrategy } from "./steiner";
import { InverseHybridStrategy } from "./inverse-hybrid";
import { ColdNumbersStrategy, HotNumbersStrategy } from "./frequency";

class SeededRandom {
  private seedValue: number;

  constructor(seedStr: string) {
    let hash = 5381;
    for (let i = 0; i < seedStr.length; i++) {
      hash = (hash * 33) ^ seedStr.charCodeAt(i);
    }
    this.seedValue = hash >>> 0;
  }

  private next(): number {
    this.seedValue = (this.seedValue * 1664525 + 1013904223) >>> 0;
    return this.seedValue / 0xffffffff;
  }

  sample<T>(array: T[], k: number): T[] {
    const arr = [...array];
    const n = arr.length;
    const result: T[] = [];
    for (let i = 0; i < Math.min(k, n); i++) {
      const idx = Math.floor(this.next() * arr.length);
      result.push(arr[idx]);
      arr.splice(idx, 1);
    }
    return result;
  }
}

export class PatternStrategy extends PredictModel {
  lookbackDays: number;
  private rangeSize: number;
  private ranges: [number, number][];

  constructor(
    df: DrawRow[],
    timePredict = 1,
    minVal = PredictModel.POWER_655_MIN_VAL,
    maxVal = PredictModel.POWER_655_MAX_VAL,
  ) {
    super(df, timePredict, minVal, maxVal);
    this.lookbackDays = 180;
    this.rangeSize = Math.floor((maxVal - minVal + 1) / 5);
    this.ranges = Array.from({ length: 5 }, (_, i) => [
      minVal + i * this.rangeSize,
      i < 4 ? minVal + (i + 1) * this.rangeSize - 1 : maxVal,
    ]);
  }

  predict(targetDate: string, candidatePool?: number[] | null): number[] {
    // Bypassed/simplified for proposal only since we only use it as proposer in Trio
    const pool = candidatePool ?? Array.from({ length: this.maxVal - this.minVal + 1 }, (_, i) => this.minVal + i);
    const sample = [...pool];
    const out: number[] = [];
    for (let i = 0; i < Math.min(this.numberPredict, sample.length); i++) {
      const idx = Math.floor(Math.random() * sample.length);
      out.push(sample[idx]);
      sample.splice(idx, 1);
    }
    return out.sort((a, b) => a - b);
  }

  proposeTopNumbers(targetDate: string, k: number): number[] {
    const target = new Date(targetDate).getTime();
    const start = target - this.lookbackDays * 86_400_000;
    const rangeCounts = [0, 0, 0, 0, 0];
    let total = 0;

    for (const row of this.dfSorted) {
      const t = new Date(row.date).getTime();
      if (t >= target) continue;
      if (t < start) continue;

      const nums = this.mainNumbers(row.result);
      for (const num of nums) {
        const bucket = Math.min(Math.floor((num - this.minVal) / this.rangeSize), 4);
        rangeCounts[bucket]++;
        total++;
      }
    }

    if (total === 0) {
      return Array.from({ length: Math.min(k, this.maxVal - this.minVal + 1) }, (_, i) => this.minVal + i);
    }

    const perBucket = rangeCounts.map((count) => Math.max(1, Math.round((k * count) / total)));
    const sum = perBucket.reduce((a, b) => a + b, 0);
    const drift = k - sum;
    for (let i = 0; i < Math.abs(drift); i++) {
      perBucket[i % 5] += drift > 0 ? 1 : -1;
    }

    const seed = `pattern-${targetDate}-${k}`;
    const rng = new SeededRandom(seed);

    const chosen: number[] = [];
    for (let i = 0; i < 5; i++) {
      const [lo, hi] = this.ranges[i];
      const bucketPool: number[] = [];
      for (let num = lo; num <= hi; num++) bucketPool.push(num);
      if (bucketPool.length === 0) continue;
      const take = Math.min(perBucket[i], bucketPool.length);
      chosen.push(...rng.sample(bucketPool, take));
    }

    const chosenSet = new Set(chosen);
    if (chosen.length < k) {
      for (let n = this.minVal; n <= this.maxVal; n++) {
        if (!chosenSet.has(n)) {
          chosen.push(n);
          chosenSet.add(n);
        }
        if (chosen.length === k) break;
      }
    }
    return chosen.slice(0, k).sort((a, b) => a - b);
  }
}

export class InverseHybridTrioStrategy extends PredictModel {
  steiner: SteinerStrategy;
  topK: number;
  private callCounter = 0;

  stratCold: InverseHybridStrategy;
  stratPair: InverseHybridStrategy;
  stratPattern: InverseHybridStrategy;
  subStrategies: InverseHybridStrategy[];

  constructor(
    df: DrawRow[],
    steiner: SteinerStrategy,
    options: { topK?: number; timePredict?: number } = {},
  ) {
    const timePredict = options.timePredict ?? 6;
    super(steiner.df, timePredict, steiner.minVal, steiner.maxVal);

    this.steiner = steiner;
    this.topK = options.topK ?? 15;

    // Instantiate sub-strategies with TPD = 2 (to buy 2 tickets per strategy)
    this.stratCold = new InverseHybridStrategy(
      new ColdNumbersStrategy(df, 2, this.minVal, this.maxVal, {
        lookbackDays: 365,
        selectionWeight: 0.7,
      }),
      steiner,
      { topK: this.topK, coverage: 2, timePredict: 2 },
    );

    // Pair Frequency proposer is equivalent to HotNumbers proposer in Python
    this.stratPair = new InverseHybridStrategy(
      new HotNumbersStrategy(df, 2, this.minVal, this.maxVal, {
        lookbackDays: 365,
      }),
      steiner,
      { topK: this.topK, coverage: 2, timePredict: 2 },
    );

    this.stratPattern = new InverseHybridStrategy(
      new PatternStrategy(df, 2, this.minVal, this.maxVal),
      steiner,
      { topK: this.topK, coverage: 2, timePredict: 2 },
    );

    this.subStrategies = [this.stratCold, this.stratPair, this.stratPattern];
  }

  applyProductConfig(config: any) {
    super.applyProductConfig(config);
    for (const strat of this.subStrategies) {
      strat.applyProductConfig(config);
    }
    return this;
  }

  predict(targetDate: string, candidatePool?: number[] | null): number[] {
    const idx = this.callCounter;
    this.callCounter++;

    const ticketIdx = Math.floor(idx / this.subStrategies.length);
    
    // Set private field via any-cast
    (this.steiner as any).callCounter = ticketIdx;

    const chosenStrat = this.subStrategies[idx % this.subStrategies.length];
    return chosenStrat.predict(targetDate, candidatePool);
  }
}
