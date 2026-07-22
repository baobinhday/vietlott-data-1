# 🔮 Vietlott Power 655 Hybrid Prediction Summary

> **Generated**: 2026-07-22 17:29:45
>
> This document compares **hybrid** strategies where Steiner proposes top-K
> candidate tickets (each = 2 disjoint Steiner triples) and a voter strategy
> re-scores them via its native signal.
>
> This is an experimental module for educational purposes only.

## 📊 Hybrid Strategy Performance Comparison

> Sorted by ROI (best → worst).  All strategies backtested with **30 tickets/draw**.
> Each hybrid uses Steiner as proposer (top-15 number pool) and a voter
> strategy is invoked with ``candidate_pool`` set to that pool.

| Rank | Strategy | Total Cost (VND) | Total Gain (VND) | Net Profit (VND) | ROI |
|------|----------|-----------------|-----------------|-----------------|-----|
| 🥇 1 | Hybrid: Steiner + Exponential Decay | 412,200,000 | 187,400,000 | -224,800,000 | -54.54% |
| 🥈 2 | Hybrid: Steiner + Hot Numbers | 412,200,000 | 148,300,000 | -263,900,000 | -64.02% |
| 🥉 3 | Hybrid: Steiner + Cold Numbers | 412,200,000 | 145,650,000 | -266,550,000 | -64.67% |
|    4 | Hybrid: Steiner + Pair Frequency | 412,200,000 | 141,900,000 | -270,300,000 | -65.57% |
|    5 | Steiner Strategy | 412,200,000 | 105,500,000 | -306,700,000 | -74.41% |
|    6 | Hybrid: Steiner + Long Absence | 412,200,000 | 101,550,000 | -310,650,000 | -75.36% |
|    7 | Hybrid: Steiner + Markov Chain | 412,200,000 | 63,100,000 | -349,100,000 | -84.69% |
|    8 | Hybrid: Steiner + Not Repeat | 412,200,000 | 60,000,000 | -352,200,000 | -85.44% |


## 🔮 Hybrid Prediction Models

> ⚠️ **Disclaimer**: These are experimental models for educational purposes only. Lottery outcomes are random and cannot be predicted reliably.

### 🎲 Steiner Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Steiner Strategy |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 105,500,000 VND |
| Net profit/loss | -306,700,000 VND |
| ROI | -74.41% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 57 times
  - **3 matches**: 740 times
  - **2 matches**: 5,598 times
  - **1 matches**: 17,135 times
  - **0 matches**: 17,689 times

#### Best Results (5+ matches)
| date                | result                      | predicted               |   correct_num |
|:--------------------|:----------------------------|:------------------------|--------------:|
| 2021-09-25 00:00:00 | [7, 20, 27, 43, 48, 51, 37] | [7, 19, 20, 27, 43, 48] |             5 |

### 🎲 Hybrid: Steiner + Pair Frequency

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Pair Frequency |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 141,900,000 VND |
| Net profit/loss | -270,300,000 VND |
| ROI | -65.57% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 44 times
  - **3 matches**: 798 times
  - **2 matches**: 5,348 times
  - **1 matches**: 16,857 times
  - **0 matches**: 18,171 times

#### Best Results (5+ matches)
| date                | result                    | predicted             |   correct_num |
|:--------------------|:--------------------------|:----------------------|--------------:|
| 2019-03-02 00:00:00 | [1, 2, 3, 20, 46, 48, 31] | [1, 2, 3, 8, 31, 48]  |             5 |
| 2019-03-02 00:00:00 | [1, 2, 3, 20, 46, 48, 31] | [1, 2, 3, 12, 31, 48] |             5 |

### 🎲 Hybrid: Steiner + Hot Numbers

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Hot Numbers |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 148,300,000 VND |
| Net profit/loss | -263,900,000 VND |
| ROI | -64.02% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 60 times
  - **3 matches**: 766 times
  - **2 matches**: 5,401 times
  - **1 matches**: 16,671 times
  - **0 matches**: 18,320 times

#### Best Results (5+ matches)
| date                | result                     | predicted              |   correct_num |
|:--------------------|:---------------------------|:-----------------------|--------------:|
| 2018-06-21 00:00:00 | [2, 8, 19, 23, 25, 33, 32] | [2, 8, 23, 24, 25, 32] |             5 |
| 2017-12-23 00:00:00 | [7, 8, 9, 13, 28, 44, 12]  | [7, 8, 9, 12, 13, 37]  |             5 |

### 🎲 Hybrid: Steiner + Cold Numbers

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Cold Numbers |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 145,650,000 VND |
| Net profit/loss | -266,550,000 VND |
| ROI | -64.67% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 54 times
  - **3 matches**: 773 times
  - **2 matches**: 5,342 times
  - **1 matches**: 16,691 times
  - **0 matches**: 18,358 times

#### Best Results (5+ matches)
| date                | result                      | predicted              |   correct_num |
|:--------------------|:----------------------------|:-----------------------|--------------:|
| 2019-04-20 00:00:00 | [8, 10, 12, 24, 40, 44, 51] | [4, 8, 12, 24, 40, 51] |             5 |
| 2018-12-18 00:00:00 | [1, 9, 15, 17, 25, 26, 8]   | [1, 8, 15, 25, 26, 49] |             5 |

### 🎲 Hybrid: Steiner + Long Absence

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Long Absence |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 101,550,000 VND |
| Net profit/loss | -310,650,000 VND |
| ROI | -75.36% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 45 times
  - **3 matches**: 781 times
  - **2 matches**: 5,431 times
  - **1 matches**: 16,913 times
  - **0 matches**: 18,049 times

#### Best Results (5+ matches)
| date                | result                    | predicted             |   correct_num |
|:--------------------|:--------------------------|:----------------------|--------------:|
| 2019-03-02 00:00:00 | [1, 2, 3, 20, 46, 48, 31] | [1, 2, 3, 31, 42, 48] |             5 |

### 🎲 Hybrid: Steiner + Not Repeat

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Not Repeat |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 60,000,000 VND |
| Net profit/loss | -352,200,000 VND |
| ROI | -85.44% |

#### Match Distribution
  - **4 matches**: 47 times
  - **3 matches**: 730 times
  - **2 matches**: 5,441 times
  - **1 matches**: 17,091 times
  - **0 matches**: 17,911 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### 🎲 Hybrid: Steiner + Exponential Decay

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Exponential Decay |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 187,400,000 VND |
| Net profit/loss | -224,800,000 VND |
| ROI | -54.54% |

#### Match Distribution
  - **5 matches**: 3 times
  - **4 matches**: 53 times
  - **3 matches**: 818 times
  - **2 matches**: 5,346 times
  - **1 matches**: 16,878 times
  - **0 matches**: 18,122 times

#### Best Results (5+ matches)
| date                | result                       | predicted                |   correct_num |
|:--------------------|:-----------------------------|:-------------------------|--------------:|
| 2026-02-07 00:00:00 | [3, 5, 13, 15, 29, 46, 1]    | [1, 3, 4, 5, 15, 29]     |             5 |
| 2019-03-02 00:00:00 | [1, 2, 3, 20, 46, 48, 31]    | [1, 2, 3, 8, 31, 48]     |             5 |
| 2017-09-14 00:00:00 | [22, 23, 32, 43, 44, 51, 15] | [15, 19, 23, 32, 43, 51] |             5 |

### 🎲 Hybrid: Steiner + Markov Chain

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hybrid: Steiner + Markov Chain |
| Tickets per day | 30 |
| Ticket price | 10,000 VND |
| Number range | 1 - 55 |
| Numbers to pick | 6 |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | 2017-08-01 00:00:00 |
| End date | 2026-07-21 00:00:00 |
| Total draws | 1,374 |
| Total predictions | 41,220 |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | 412,200,000 VND |
| Total gain | 63,100,000 VND |
| Net profit/loss | -349,100,000 VND |
| ROI | -84.69% |

#### Match Distribution
  - **4 matches**: 46 times
  - **3 matches**: 802 times
  - **2 matches**: 5,479 times
  - **1 matches**: 16,946 times
  - **0 matches**: 17,947 times

#### Best Results (5+ matches)
No results with 5+ matches found.




---

## ⚠️ Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random and cannot be reliably predicted. Never gamble more than you can afford to lose.
