// Inverse hybrid prediction strategy (port of strategies/inverse_hybrid.py).
//
// Direction: a *proposer* strategy outputs a top-K candidate pool, then
// Steiner picks ``numberPredict`` numbers from that pool using its
// pair-disjoint triple decomposition with the requested coverage.

import { PredictModel } from "./base";
import { SteinerStrategy } from "./steiner";

export interface InverseHybridOptions {
  topK?: number;
  coverage?: number;
  timePredict?: number;
}

export class InverseHybridStrategy extends PredictModel {
  proposer: PredictModel;
  steiner: SteinerStrategy;
  topK: number;
  coverage: number;

  constructor(proposer: PredictModel, steiner: SteinerStrategy, options: InverseHybridOptions = {}) {
    super(
      steiner.df,
      options.timePredict ?? 1,
      proposer.minVal,
      proposer.maxVal,
    );
    this.proposer = proposer;
    this.steiner = steiner;
    this.topK = options.topK ?? 15;
    this.coverage = options.coverage ?? 3;
    this.ticketPrice = proposer.ticketPrice;
    this.numberPredict = proposer.numberPredict;
    this.hasSpecial = proposer.hasSpecial;
    this.specialPosition = proposer.specialPosition;
    this.specialPickRequired = proposer.specialPickRequired;
    this.specialMin = proposer.specialMin;
    this.specialMax = proposer.specialMax;
    this.specialCount = proposer.specialCount;
    this.productName = proposer.productName;
    this.prizeFn = proposer.prizeFn;
  }

  predict(targetDate: string, _candidatePool?: number[] | null): number[] {
    let pool: number[];
    try {
      pool = this.proposer.proposeTopNumbers(targetDate, this.topK);
    } catch {
      pool = this.proposer.proposeTopNumbers(targetDate, this.topK);
    }
    if (!pool || !pool.length) return this.steiner.predict(targetDate);
    return this.steiner.predictFromPool(targetDate, pool, this.coverage, this.numberPredict);
  }
}
