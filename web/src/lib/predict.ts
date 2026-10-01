// Prediction engine — generates the next-draw tickets using the same
// strategy chain as the backtest, but with no actual result to compare against.

import type { BacktestConfig, Draw, PredictionResult, PredictionTicket, ProductConfig } from "./types";
import { loadDraws, loadPrizes } from "./data";
import { InverseHybridStrategy } from "./strategies/inverse-hybrid";
import { ColdNumbersStrategy } from "./strategies/frequency";
import { SteinerStrategy } from "./strategies/steiner";
import { applyFrequencySpecials } from "./strategies/specials";
import { InverseHybridTrioStrategy } from "./strategies/trio";

/**
 * Generate prediction tickets for the *next* draw.  The target date is the
 * most recent draw date + 1 day (so the strategy can use every historical
 * draw as lookback).
 *
 * Ticket count mirrors the Python backtest: for every main prediction
 * (``TPD`` unique mains) we wheel through the chosen specials
 * (``top_n`` specials), giving ``TPD * top_n`` ticket rows per draw.
 * If the product has no special pick required (e.g. 6/45) the special
 * wheel collapses and we get just ``TPD`` tickets.
 */
export function generatePrediction(
  product: ProductConfig,
  config: BacktestConfig,
): PredictionResult {
  const draws = loadDraws(product);
  // Prize records are only needed by the backtest path. The prediction
  // route doesn't have a draw result to look up so we skip the load.
  void loadPrizes(product);
  const df = draws.map((d) => ({ date: d.date, id: d.id, result: d.result }));
  const previousDraw: Draw | null = draws[0] ?? null;

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
  if (product.specialPickRequired && product.name === "power_535") {
    applyFrequencySpecials(strategy, {
      topN: config.specials.topN,
      lookbackDraws: config.specials.lookbackDraws,
      offsetDraws: config.specials.offsetDraws,
      mode: config.specials.mode,
    });
  }

  // The target date is "after the latest draw" — use the day after the
  // most recent draw.  This ensures every historical row is available as
  // lookback.
  const targetDate = previousDraw ? addDays(previousDraw.date, 1) : new Date().toISOString().slice(0, 10);

  // TPD main predictions.
  const mainTickets: number[][] = [];
  for (let i = 0; i < config.tpd; i++) {
    mainTickets.push(strategy.predict(targetDate));
  }
  // Specials — the wheel we generated for the next draw.  Empty when the
  // product has no special pick required (e.g. 6/45) or when the
  // frequency picker returned nothing.
  const specials = product.specialPickRequired ? strategy.predictSpecial(targetDate) : [];

  // Cartesian product: every (main, special) combination becomes a ticket.
  // For non-special products the special list collapses to [null] so we
  // emit exactly TPD rows.
  const specialList: (number | null)[] = specials.length ? specials : [null];
  const tickets: PredictionTicket[] = [];
  let coverage = 1;
  for (let i = 0; i < mainTickets.length; i++) {
    for (let si = 0; si < specialList.length; si++) {
      tickets.push({
        predicted: mainTickets[i],
        predictedSpecial: specialList[si],
        coverage: coverage++,
      });
    }
  }

  return {
    product: product.name,
    productDisplay: product.display,
    strategy: config.strategy ?? "Inverse Hybrid: Cold Numbers → Steiner",
    config,
    previousDraw,
    tickets,
    generatedAt: new Date().toISOString(),
  };
}

function addDays(iso: string, n: number): string {
  const d = new Date(iso);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
