// Base class for all lottery prediction strategies (port of machine_learning/strategies/base.py).
//
// All concrete strategy classes extend ``PredictModel`` and override ``predict(date)``.
// The base class provides shared constants and helpers (main-numbers slicing,
// match-count comparison).

import type { ProductConfig } from "../types";

export abstract class PredictModel {
  static POWER_655_MIN_VAL = 1;
  static POWER_655_MAX_VAL = 55;
  static number_predict = 6;
  static ticket_price = 10000;

  static prices: Record<number, number> = {
    6: 30_000_000_000,
    5: 40_000_000,
    4: 500_000,
    3: 50_000,
  };

  static col_main_match = "main_match";
  static col_special_match = "special_match";
  static col_correct = "is_correct";
  static col_correct_num = "correct_num";

  // --- Per-product config (set via applyProductConfig) ---
  mainCount: number = 6;
  mainMin: number = 1;
  mainMax: number = 55;

  hasSpecial = false;
  specialPosition = 0;
  specialPickRequired = false;
  specialMin = 0;
  specialMax = 0;
  specialCount = 1;

  includeSpecialInTraining = false;

  // --- Per-instance state ---
  df: DrawRow[] = [];
  dfSorted: DrawRow[] = [];
  timePredict = 1;
  minVal: number;
  maxVal: number;
  numberPredict: number;
  ticketPrice: number;
  productName: string | null = null;
  prizeFn: ((m: number, s: number) => number) | null = null;

  constructor(df: DrawRow[], timePredict: number, minVal: number, maxVal: number) {
    this.df = df;
    this.dfSorted = [...df].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
    this.timePredict = timePredict;
    this.minVal = minVal;
    this.maxVal = maxVal;
    this.numberPredict = Math.max(1, maxVal - minVal + 1);
    this.ticketPrice = PredictModel.ticket_price;
  }

  applyProductConfig(config: ProductConfig): this {
    this.mainMin = config.minValue;
    this.mainMax = config.maxValue;
    this.mainCount = config.sizeOutput;
    this.minVal = config.minValue;
    this.maxVal = config.maxValue;
    this.numberPredict = config.sizeOutput;
    this.hasSpecial = config.hasSpecial;
    this.specialPosition = config.specialPosition;
    this.specialPickRequired = config.specialPickRequired;
    this.specialMin = config.specialMin;
    this.specialMax = config.specialMax;
    this.specialCount = config.specialCount;
    this.ticketPrice = config.ticketPrice;
    this.productName = config.name;
    this.prizeFn = (m, s) => fallbackPrizeForProduct(config.name, m, s);
    return this;
  }

  /** Slice the result list to the main numbers only (drop the special). */
  mainNumbers(result: number[]): number[] {
    if (this.includeSpecialInTraining) return [...result];
    if (this.hasSpecial && result.length > this.specialPosition) {
      return result.slice(0, this.specialPosition);
    }
    return [...result];
  }

  /** Return the special number from a result list, or null if no special. */
  specialNumber(result: number[]): number | null {
    if (!this.hasSpecial) return null;
    if (result.length <= this.specialPosition) return null;
    return result[this.specialPosition];
  }

  /**
   * Compare predicted main + special numbers against the actual draw result.
   * Mirrors Python ``_compare_list``.
   */
  compareList(
    predictedMain: number[],
    predictedSpecial: number | null,
    result: number[],
  ): { mainMatch: number; specialMatch: number } {
    const effectiveHasSpecial = this.hasSpecial && this.specialPosition < result.length;
    let mainResult: Set<number>;
    let specialResult: number | null;
    if (effectiveHasSpecial) {
      mainResult = new Set(result.slice(0, this.specialPosition));
      specialResult = result[this.specialPosition];
    } else {
      mainResult = new Set(result);
      specialResult = null;
    }
    const mainMatch = predictedMain.filter((n) => mainResult.has(n)).length;
    let specialMatch = 0;
    if (effectiveHasSpecial) {
      if (this.specialPickRequired) {
        if (predictedSpecial != null && predictedSpecial === specialResult) specialMatch = 1;
      } else {
        if (specialResult != null && predictedMain.includes(specialResult)) specialMatch = 1;
      }
    }
    return { mainMatch, specialMatch };
  }

  predictSpecial(_date: string, _candidatePool?: number[] | null): number[] {
    if (!this.specialPickRequired) return [];
    // Default behaviour: wheel through every special.
    return Array.from({ length: this.specialMax - this.specialMin + 1 }, (_, i) => this.specialMin + i);
  }

  proposeTopNumbers(_targetDate: string, k: number): number[] {
    return Array.from({ length: k }, (_, i) => this.minVal + i);
  }

  /**
   * The core prediction. Sub-classes MUST override.
   * Returns ``numberPredict`` distinct integers in ``[minVal, maxVal]``.
   */
  abstract predict(date: string, candidatePool?: number[] | null): number[];
}

export interface DrawRow {
  date: string;
  id: string;
  result: number[];
}

function fallbackPrizeForProduct(product: string, m: number, s: number): number {
  if (product === "power_535") {
    if (m === 5 && s === 1) return 6_000_000_000;
    if (m === 5) return 10_000_000;
    if (m === 4 && s === 1) return 5_000_000;
    if (m === 4) return 500_000;
    if (m === 3 && s === 1) return 100_000;
    if (m === 3) return 30_000;
    if (s === 1 && m >= 0) return 10_000;
    return 0;
  }
  if (product === "power_645") {
    if (m === 6) return 12_000_000_000;
    if (m === 5) return 10_000_000;
    if (m === 4) return 300_000;
    if (m === 3) return 30_000;
    return 0;
  }
  if (product === "power_655") {
    if (m === 6) return 30_000_000_000;
    if (m === 5 && s === 1) return 3_000_000_000;
    if (m === 5) return 40_000_000;
    if (m === 4) return 500_000;
    if (m === 3) return 50_000;
    return 0;
  }
  return 0;
}
