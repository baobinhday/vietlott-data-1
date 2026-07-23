# 🔮 Vietlott Power 655 Hybrid Prediction Summary

> **Generated**: 2026-07-23 11:12:03
>
> This document compares **hybrid** strategies where Steiner proposes top-K
> candidate tickets (each = 2 disjoint Steiner triples) and a voter strategy
> re-scores them via its native signal.
>
> This is an experimental module for educational purposes only.

## 📊 Hybrid Strategy Performance Comparison

> Sorted by ROI (best → worst).  All strategies backtested with **30 tickets/draw**.
>
> * **Hybrid (Steiner → voter)**: Steiner proposes the top-15 number
>   pool and a voter strategy picks 6 using its own algorithm.
> * **Inverse Hybrid (voter → Steiner)**: a voter strategy proposes the
>   top-15 candidate pool and Steiner picks 6 from it using pair-disjoint
>   triple decomposition with coverage 3 (3 disjoint (T1, T2) tickets).

| Rank | Strategy | Total Cost (VND) | Total Gain (VND) | Net Profit (VND) | ROI |
|------|----------|-----------------|-----------------|-----------------|-----|
| 🥇 1 | Inverse Hybrid: Pair Frequency → Steiner (cov 3) | 412,200,000 | 449,500,000 | 37,300,000 | 9.05% |
| 🥈 2 | Inverse Hybrid: Hot Numbers → Steiner (cov 3) | 412,200,000 | 449,000,000 | 36,800,000 | 8.93% |
| 🥉 3 | Hybrid: Steiner + Hot Numbers | 412,200,000 | 186,100,000 | -226,100,000 | -54.85% |
|    4 | Hybrid: Steiner + Not Repeat | 412,200,000 | 134,000,000 | -278,200,000 | -67.49% |
|    5 | Steiner Strategy | 412,200,000 | 105,500,000 | -306,700,000 | -74.41% |
|    6 | Hybrid: Steiner + Long Absence | 412,200,000 | 103,200,000 | -309,000,000 | -74.96% |
|    7 | Hybrid: Steiner + Exponential Decay | 412,200,000 | 102,000,000 | -310,200,000 | -75.25% |
|    8 | Hybrid: Steiner + Markov Chain | 412,200,000 | 101,900,000 | -310,300,000 | -75.28% |
|    9 | Hybrid: Steiner + Cold Numbers | 412,200,000 | 100,200,000 | -312,000,000 | -75.69% |
|    10 | Inverse Hybrid: Long Absence → Steiner (cov 3) | 412,200,000 | 85,000,000 | -327,200,000 | -79.38% |
|    11 | Inverse Hybrid: Exponential Decay → Steiner (cov 3) | 412,200,000 | 78,500,000 | -333,700,000 | -80.96% |
|    12 | Inverse Hybrid: Markov Chain → Steiner (cov 3) | 412,200,000 | 76,500,000 | -335,700,000 | -81.44% |
|    13 | Inverse Hybrid: Pattern → Steiner (cov 3) | 412,200,000 | 75,500,000 | -336,700,000 | -81.68% |
|    14 | Inverse Hybrid: Not Repeat → Steiner (cov 3) | 412,200,000 | 73,500,000 | -338,700,000 | -82.17% |
|    15 | Inverse Hybrid: Cold Numbers → Steiner (cov 3) | 412,200,000 | 71,500,000 | -340,700,000 | -82.65% |
|    16 | Hybrid: Steiner + Pair Frequency | 412,200,000 | 58,150,000 | -354,050,000 | -85.89% |


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
| date                | result                      | predicted               | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:------------------------|:--------------------|----------------:|--------------:|
| 2021-09-25 00:00:00 | [7, 20, 27, 43, 48, 51, 37] | [7, 19, 20, 27, 43, 48] |                     |               0 |             5 |

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
| Total gain | 58,150,000 VND |
| Net profit/loss | -354,050,000 VND |
| ROI | -85.89% |

#### Match Distribution
  - **4 matches**: 39 times
  - **3 matches**: 773 times
  - **2 matches**: 5,545 times
  - **1 matches**: 16,707 times
  - **0 matches**: 18,156 times

#### Best Results (5+ matches)
No results with 5+ matches found.

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
| Total gain | 186,100,000 VND |
| Net profit/loss | -226,100,000 VND |
| ROI | -54.85% |

#### Match Distribution
  - **5 matches**: 3 times
  - **4 matches**: 52 times
  - **3 matches**: 802 times
  - **2 matches**: 5,546 times
  - **1 matches**: 16,703 times
  - **0 matches**: 18,114 times

#### Best Results (5+ matches)
| date                | result                     | predicted             | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:----------------------|:--------------------|----------------:|--------------:|
| 2022-03-10 00:00:00 | [1, 3, 8, 16, 19, 36, 41]  | [1, 3, 4, 8, 16, 41]  |                     |               0 |             5 |
| 2019-07-11 00:00:00 | [6, 9, 15, 26, 35, 38, 34] | [5, 6, 9, 15, 34, 35] |                     |               0 |             5 |
| 2018-06-21 00:00:00 | [2, 8, 19, 23, 25, 33, 32] | [2, 3, 8, 23, 25, 32] |                     |               0 |             5 |

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
| Total gain | 100,200,000 VND |
| Net profit/loss | -312,000,000 VND |
| ROI | -75.69% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 43 times
  - **3 matches**: 774 times
  - **2 matches**: 5,403 times
  - **1 matches**: 16,776 times
  - **0 matches**: 18,223 times

#### Best Results (5+ matches)
| date                | result                    | predicted            | predicted_special   |   special_match |   correct_num |
|:--------------------|:--------------------------|:---------------------|:--------------------|----------------:|--------------:|
| 2022-03-10 00:00:00 | [1, 3, 8, 16, 19, 36, 41] | [1, 2, 3, 8, 16, 41] |                     |               0 |             5 |

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
| Total gain | 103,200,000 VND |
| Net profit/loss | -309,000,000 VND |
| ROI | -74.96% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 43 times
  - **3 matches**: 834 times
  - **2 matches**: 5,442 times
  - **1 matches**: 16,875 times
  - **0 matches**: 18,025 times

#### Best Results (5+ matches)
| date                | result                    | predicted            | predicted_special   |   special_match |   correct_num |
|:--------------------|:--------------------------|:---------------------|:--------------------|----------------:|--------------:|
| 2020-10-01 00:00:00 | [3, 6, 7, 19, 38, 54, 50] | [3, 4, 6, 7, 19, 50] |                     |               0 |             5 |

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
| Total gain | 134,000,000 VND |
| Net profit/loss | -278,200,000 VND |
| ROI | -67.49% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 37 times
  - **3 matches**: 710 times
  - **2 matches**: 5,421 times
  - **1 matches**: 17,218 times
  - **0 matches**: 17,832 times

#### Best Results (5+ matches)
| date                | result                    | predicted             | predicted_special   |   special_match |   correct_num |
|:--------------------|:--------------------------|:----------------------|:--------------------|----------------:|--------------:|
| 2017-11-09 00:00:00 | [2, 3, 6, 23, 34, 36, 50] | [2, 3, 6, 23, 35, 36] |                     |               0 |             5 |
| 2017-11-09 00:00:00 | [2, 3, 6, 23, 34, 36, 50] | [2, 3, 6, 23, 36, 41] |                     |               0 |             5 |

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
| Total gain | 102,000,000 VND |
| Net profit/loss | -310,200,000 VND |
| ROI | -75.25% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 48 times
  - **3 matches**: 760 times
  - **2 matches**: 5,454 times
  - **1 matches**: 16,840 times
  - **0 matches**: 18,117 times

#### Best Results (5+ matches)
| date                | result                    | predicted            | predicted_special   |   special_match |   correct_num |
|:--------------------|:--------------------------|:---------------------|:--------------------|----------------:|--------------:|
| 2017-12-23 00:00:00 | [7, 8, 9, 13, 28, 44, 12] | [6, 7, 8, 9, 12, 13] |                     |               0 |             5 |

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
| Total gain | 101,900,000 VND |
| Net profit/loss | -310,300,000 VND |
| ROI | -75.28% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 41 times
  - **3 matches**: 828 times
  - **2 matches**: 5,406 times
  - **1 matches**: 16,934 times
  - **0 matches**: 18,010 times

#### Best Results (5+ matches)
| date                | result                    | predicted              | predicted_special   |   special_match |   correct_num |
|:--------------------|:--------------------------|:-----------------------|:--------------------|----------------:|--------------:|
| 2026-02-07 00:00:00 | [3, 5, 13, 15, 29, 46, 1] | [3, 5, 13, 15, 29, 37] |                     |               0 |             5 |

### 🎲 Inverse Hybrid: Pair Frequency → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Pair Frequency → Steiner (cov 3) |
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
| Total gain | 449,500,000 VND |
| Net profit/loss | 37,300,000 VND |
| ROI | 9.05% |

#### Match Distribution
  - **5 matches**: 10 times
  - **4 matches**: 10 times
  - **3 matches**: 890 times
  - **2 matches**: 5,690 times
  - **1 matches**: 17,120 times
  - **0 matches**: 17,500 times

#### Best Results (5+ matches)
| date                | result                     | predicted              | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:-----------------------|:--------------------|----------------:|--------------:|
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |

### 🎲 Inverse Hybrid: Hot Numbers → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Hot Numbers → Steiner (cov 3) |
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
| Total gain | 449,000,000 VND |
| Net profit/loss | 36,800,000 VND |
| ROI | 8.93% |

#### Match Distribution
  - **5 matches**: 10 times
  - **4 matches**: 10 times
  - **3 matches**: 880 times
  - **2 matches**: 5,720 times
  - **1 matches**: 17,110 times
  - **0 matches**: 17,490 times

#### Best Results (5+ matches)
| date                | result                     | predicted              | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:-----------------------|:--------------------|----------------:|--------------:|
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15] | [3, 9, 15, 17, 23, 49] |                     |               0 |             5 |

### 🎲 Inverse Hybrid: Cold Numbers → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Cold Numbers → Steiner (cov 3) |
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
| Total gain | 71,500,000 VND |
| Net profit/loss | -340,700,000 VND |
| ROI | -82.65% |

#### Match Distribution
  - **4 matches**: 60 times
  - **3 matches**: 830 times
  - **2 matches**: 5,920 times
  - **1 matches**: 16,930 times
  - **0 matches**: 17,480 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### 🎲 Inverse Hybrid: Long Absence → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Long Absence → Steiner (cov 3) |
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
| Total gain | 85,000,000 VND |
| Net profit/loss | -327,200,000 VND |
| ROI | -79.38% |

#### Match Distribution
  - **4 matches**: 70 times
  - **3 matches**: 1,000 times
  - **2 matches**: 5,790 times
  - **1 matches**: 16,320 times
  - **0 matches**: 18,040 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### 🎲 Inverse Hybrid: Not Repeat → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Not Repeat → Steiner (cov 3) |
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
| Total gain | 73,500,000 VND |
| Net profit/loss | -338,700,000 VND |
| ROI | -82.17% |

#### Match Distribution
  - **4 matches**: 50 times
  - **3 matches**: 970 times
  - **2 matches**: 5,500 times
  - **1 matches**: 16,480 times
  - **0 matches**: 18,220 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### 🎲 Inverse Hybrid: Exponential Decay → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Exponential Decay → Steiner (cov 3) |
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
| Total gain | 78,500,000 VND |
| Net profit/loss | -333,700,000 VND |
| ROI | -80.96% |

#### Match Distribution
  - **4 matches**: 90 times
  - **3 matches**: 670 times
  - **2 matches**: 6,190 times
  - **1 matches**: 16,610 times
  - **0 matches**: 17,660 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### 🎲 Inverse Hybrid: Markov Chain → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Markov Chain → Steiner (cov 3) |
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
| Total gain | 76,500,000 VND |
| Net profit/loss | -335,700,000 VND |
| ROI | -81.44% |

#### Match Distribution
  - **4 matches**: 80 times
  - **3 matches**: 730 times
  - **2 matches**: 5,910 times
  - **1 matches**: 17,000 times
  - **0 matches**: 17,500 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### 🎲 Inverse Hybrid: Pattern → Steiner (cov 3)

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Inverse Hybrid: Pattern → Steiner (cov 3) |
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
| Total gain | 75,500,000 VND |
| Net profit/loss | -336,700,000 VND |
| ROI | -81.68% |

#### Match Distribution
  - **4 matches**: 60 times
  - **3 matches**: 910 times
  - **2 matches**: 5,980 times
  - **1 matches**: 17,200 times
  - **0 matches**: 17,070 times

#### Best Results (5+ matches)
No results with 5+ matches found.




---

## ⚠️ Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random and cannot be reliably predicted. Never gamble more than you can afford to lose.
