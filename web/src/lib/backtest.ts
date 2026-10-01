// Backtest engine — mirrors the loop in render_prediction_base.py::_build_and_run_strategies
// and the report generation in _generate_strategy_report.

import type {
  BacktestConfig,
  BacktestSummary,
  BacktestTicketRow,
  Draw,
  PrizeRecord,
  ProductConfig,
  YearlyRow,
} from "./types";
import { loadDraws, loadPrizes } from "./data";
import { getActualPrizeForDraw } from "./prizes";
import { InverseHybridStrategy } from "./strategies/inverse-hybrid";
import { ColdNumbersStrategy } from "./strategies/frequency";
import { SteinerStrategy } from "./strategies/steiner";
import { applyFrequencySpecials } from "./strategies/specials";
import { InverseHybridTrioStrategy } from "./strategies/trio";

function defaultBacktestConfig(product: ProductConfig): BacktestConfig {
  return {
    tpd: 2,
    cold: {
      lookbackDays: 365,
      selectionWeight: 0.7,
    },
    steiner: {
      lookbackDays: 365,
      filterConsecutive: true,
      filterSameDecade: true,
      t: 2,
      k: 3,
      v: product.steinerSystem[2],
    },
    inverse: {
      topK: 15,
    },
    specials: {
      topN: 4,
      mode: "markov_steiner",
      lookbackDraws: 60,
      offsetDraws: 30,
    },
    ddFilter: {
      enabled: true,
      threshold: 15_000_000_000,
    },
    dateFrom: null,
    dateTo: null,
  };
}

export function getDefaultBacktestConfig(product: ProductConfig): BacktestConfig {
  return defaultBacktestConfig(product);
}

/** Load the set of draw ids whose jackpot > ddThreshold (for 5/35's DD filter). */
function loadEligibleDrawIds(
  product: ProductConfig,
  prizeRecords: PrizeRecord[],
  threshold: number,
): Set<string> | null {
  if (!prizeRecords.length) return null;
  const eligible = new Set<string>();
  for (const rec of prizeRecords) {
    let ddVal = 0;
    for (const p of rec.prizes) {
      if (p.prize_name === "Giải Độc Đắc") {
        const raw = String(p.prize_value ?? "0").replace(/[.,\s]/g, "");
        const n = Number(raw);
        if (Number.isFinite(n)) ddVal = Math.trunc(n);
        break;
      }
    }
    if (ddVal > threshold) eligible.add(rec.id);
  }
  return eligible.size > 0 ? eligible : null;
}

interface RunResult {
  rows: BacktestTicketRow[];
  totalCost: number;
  totalGain: number;
  ticketPrice: number;
  bestThreshold: number;
}

function runBacktest(
  product: ProductConfig,
  draws: Draw[],
  prizeRecords: PrizeRecord[],
  config: BacktestConfig,
): RunResult {
  const df = draws.map((d) => ({ date: d.date, id: d.id, result: d.result }));
  // Build the strategy.
  const steiner = new SteinerStrategy(df, 1, product.minValue, product.maxValue, {
    lookbackDays: config.steiner.lookbackDays,
    filterConsecutive: config.steiner.filterConsecutive,
    filterSameDecade: config.steiner.filterSameDecade,
    t: config.steiner.t,
    k: config.steiner.k,
    v: config.steiner.v,
  });
  let strategy: any;
  if (config.strategy === "Inverse Hybrid: Trio (Cold + PairFreq + Pattern)") {
    strategy = new InverseHybridTrioStrategy(df, steiner, {
      topK: config.inverse.topK,
      timePredict: config.tpd,
    });
  } else {
    const proposer = new ColdNumbersStrategy(df, config.tpd, product.minValue, product.maxValue, {
      lookbackDays: config.cold.lookbackDays,
      selectionWeight: config.cold.selectionWeight,
    });
    strategy = new InverseHybridStrategy(proposer, steiner, {
      topK: config.inverse.topK,
      coverage: config.tpd,
      timePredict: config.tpd,
    });
  }
  strategy.applyProductConfig(product);

  // Specials override (only when product has special pick required)
  if (product.specialPickRequired && product.name === "power_535") {
    applyFrequencySpecials(strategy, {
      topN: config.specials.topN,
      lookbackDraws: config.specials.lookbackDraws,
      offsetDraws: config.specials.offsetDraws,
      mode: config.specials.mode,
    });
  }

  // Filter draws by date range and DD filter.
  let working = [...df];
  if (config.dateFrom) working = working.filter((r) => r.date >= config.dateFrom!);
  if (config.dateTo) working = working.filter((r) => r.date <= config.dateTo!);

  let eligibleIds: Set<string> | null = null;
  if (config.ddFilter.enabled && product.name === "power_535") {
    eligibleIds = loadEligibleDrawIds(product, prizeRecords, config.ddFilter.threshold);
  }
  if (eligibleIds) {
    working = working.filter((r) => eligibleIds!.has(r.id));
  }

  const rows: BacktestTicketRow[] = [];
  let totalCost = 0;
  let totalGain = 0;
  const ticketPrice = product.ticketPrice;

  for (const row of working) {
    // The strategy uses strictly prior data (predictors are date-based).
    for (let i = 0; i < strategy.timePredict; i++) {
      const predicted = strategy.predict(row.date);
      const specials = strategy.predictSpecial(row.date);
      const specialList = specials.length ? specials : [null];
      for (let si = 0; si < specialList.length; si++) {
        const sp = specialList[si];
        const { mainMatch, specialMatch } = strategy.compareList(predicted, sp, row.result);
        const isCorrect = mainMatch === product.sizeOutput;
        let gain = 0;
        if (product.name === "power_535") {
          gain = getActualPrizeForDraw(product.name, prizeRecords, row.id, mainMatch, specialMatch);
        } else {
          // No real prize file for non-535 products yet — use fallback.
          gain = strategy.prizeFn ? strategy.prizeFn(mainMatch, specialMatch) : 0;
        }
        rows.push({
          date: row.date,
          drawId: row.id,
          predicted,
          predictedSpecial: sp,
          result: row.result,
          mainMatch,
          specialMatch,
          gain,
          isCorrect,
          predictIdx: i,
          specialIdx: si,
        });
        totalCost += ticketPrice;
        totalGain += gain;
      }
    }
  }
  return { rows, totalCost, totalGain, ticketPrice, bestThreshold: 3 };
}

function yearlyBreakdown(rows: BacktestTicketRow[], ticketPrice: number, _bestThreshold: number): YearlyRow[] {
  const byYear = new Map<number, { draws: Set<string>; predictions: number; gain: number }>();
  for (const r of rows) {
    const y = Number(r.date.slice(0, 4));
    if (!byYear.has(y)) byYear.set(y, { draws: new Set(), predictions: 0, gain: 0 });
    const yb = byYear.get(y)!;
    yb.draws.add(r.drawId);
    yb.predictions++;
    yb.gain += r.gain;
  }
  const out: YearlyRow[] = [];
  for (const [year, v] of [...byYear.entries()].sort((a, b) => a[0] - b[0])) {
    const cost = v.predictions * ticketPrice;
    const profit = v.gain - cost;
    const roi = cost > 0 ? (profit / cost) * 100 : 0;
    out.push({
      year,
      draws: v.draws.size,
      predictions: v.predictions,
      cost,
      gain: v.gain,
      profit,
      roi,
    });
  }
  return out;
}

export function runStrategyBacktest(
  product: ProductConfig,
  config: BacktestConfig,
): BacktestSummary {
  const draws = loadDraws(product);
  const prizeRecords = loadPrizes(product);
  const result = runBacktest(product, draws, prizeRecords, config);

  const matchDist: Record<number, number> = {};
  let specialHits = 0;
  for (const r of result.rows) {
    matchDist[r.mainMatch] = (matchDist[r.mainMatch] ?? 0) + 1;
    if (r.specialMatch > 0) specialHits++;
  }
  const yearly = yearlyBreakdown(result.rows, product.ticketPrice, result.bestThreshold);
  const totalProfit = result.totalGain - result.totalCost;
  const roi = result.totalCost > 0 ? (totalProfit / result.totalCost) * 100 : 0;
  const eligibleDraws = new Set(result.rows.map((r) => r.drawId)).size;

  return {
    totalCost: result.totalCost,
    totalGain: result.totalGain,
    netProfit: totalProfit,
    roi,
    totalDraws: new Set(result.rows.map((r) => r.drawId)).size,
    totalPredictions: result.rows.length,
    matchDistribution: matchDist,
    specialHits,
    bestThreshold: result.bestThreshold,
    eligibleDraws,
    bestResults: result.rows
      .filter((r) => r.mainMatch >= result.bestThreshold)
      .sort((a, b) => b.mainMatch - a.mainMatch || b.specialMatch - a.specialMatch || a.date.localeCompare(b.date)),
    yearlyBreakdown: yearly,
    allRows: result.rows,
  };
}
