// Core domain types mirroring the Python pipeline.

export type ProductName = "power_535" | "power_645" | "power_655" | "keno" | "3d" | "3d_pro" | "bingo18";

export type SpecialsMode = "hot" | "cold" | "long_absence" | "markov_steiner" | "intersection_la_mc";

export interface ProductConfig {
  name: ProductName;
  /** Display label. */
  display: string;
  /** Path (relative to repo root) of the NDJSON file with main draw data. */
  rawPath: string;
  /** Inclusive lower bound of the main number range. */
  minValue: number;
  /** Inclusive upper bound of the main number range. */
  maxValue: number;
  /** How many main numbers form a single ticket. */
  sizeOutput: number;
  /** Whether the product has a special (bonus) number. */
  hasSpecial: boolean;
  /** 0-based index of the special number in the result list. */
  specialPosition: number;
  /** Whether the player must explicitly pick a special number. */
  specialPickRequired: boolean;
  /** Inclusive lower bound of the special number range. */
  specialMin: number;
  /** Inclusive upper bound of the special number range. */
  specialMax: number;
  /** How many specials to wheel per draw when the strategy doesn't override. */
  specialCount: number;
  /** Steiner system S(t, k, v). */
  steinerSystem: [number, number, number];
  /** Price of a single ticket in VND. */
  ticketPrice: number;
}

export interface Draw {
  /** ISO date string (YYYY-MM-DD). */
  date: string;
  /** Draw id (string for forward-compat with the Python data). */
  id: string;
  /** Result list: main numbers followed by optional special. */
  result: number[];
  /** Process time (not used in prediction, only metadata). */
  process_time?: string;
  /** Prize tiers for this draw (only populated when explicitly loaded). */
  prizes?: PrizeTier[];
}

export interface PrizeTier {
  prize_name: string;
  prize_value: string;
  winners_count: string;
}

export interface PrizeRecord {
  date: string;
  id: string;
  prizes: PrizeTier[];
}

export interface BacktestConfig {
  strategy?: string;
  // Strategy: Inverse Hybrid: Cold Numbers → Steiner
  /** Tickets per day (TPD). */
  tpd: number;
  /** ColdNumbersStrategy config */
  cold: {
    lookbackDays: number;
    selectionWeight: number;
  };
  /** SteinerStrategy config */
  steiner: {
    lookbackDays: number;
    filterConsecutive: boolean;
    filterSameDecade: boolean;
    t: number;
    k: number;
    v: number;
  };
  /** InverseHybridStrategy config */
  inverse: {
    topK: number;
  };
  /** Specials picker config (only used when product has specials) */
  specials: {
    topN: number;
    mode: SpecialsMode;
    lookbackDraws: number;
    offsetDraws: number;
  };
  /** Độc Đắc filter (5/35 only) */
  ddFilter: {
    enabled: boolean;
    threshold: number;
  };
  /** Backtest window. Null = all data. */
  dateFrom: string | null;
  dateTo: string | null;
}

export interface BacktestTicketRow {
  date: string;
  drawId: string;
  predicted: number[];
  predictedSpecial: number | null;
  result: number[];
  mainMatch: number;
  specialMatch: number;
  gain: number;
  isCorrect: boolean;
  predictIdx: number;
  specialIdx: number;
}

export interface BacktestSummary {
  totalCost: number;
  totalGain: number;
  netProfit: number;
  roi: number;
  totalDraws: number;
  totalPredictions: number;
  matchDistribution: Record<number, number>;
  specialHits: number;
  bestThreshold: number;
  eligibleDraws: number;
  bestResults: BacktestTicketRow[];
  yearlyBreakdown: YearlyRow[];
  /** All ticket rows (un-capped). Sent for the full detail table. */
  allRows: BacktestTicketRow[];
}

export interface YearlyRow {
  year: number;
  draws: number;
  predictions: number;
  cost: number;
  gain: number;
  profit: number;
  roi: number;
}

export interface PredictionTicket {
  predicted: number[];
  predictedSpecial: number | null;
  coverage: number;
}

export interface PredictionResult {
  product: string;
  productDisplay: string;
  strategy: string;
  config: BacktestConfig;
  /** Most recent draw (used as the "previous draw" reference). */
  previousDraw: Draw | null;
  /** Generated tickets for the next draw. */
  tickets: PredictionTicket[];
  generatedAt: string;
}
