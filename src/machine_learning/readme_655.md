# 🔮 Vietlott Power 655 Hybrid Prediction Summary

> **Generated**: 2026-07-23 17:18:25
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
| 🥉 3 | Hybrid: Steiner + Pair Frequency | 412,200,000 | 181,650,000 | -230,550,000 | -55.93% |
|    4 | Hybrid: Steiner + Markov Chain | 412,200,000 | 180,950,000 | -231,250,000 | -56.10% |
|    5 | Hybrid: Steiner + Hot Numbers | 412,200,000 | 140,300,000 | -271,900,000 | -65.96% |
|    6 | Steiner Strategy | 412,200,000 | 105,500,000 | -306,700,000 | -74.41% |
|    7 | Hybrid: Steiner + Long Absence | 412,200,000 | 105,100,000 | -307,100,000 | -74.50% |
|    8 | Inverse Hybrid: Long Absence → Steiner (cov 3) | 412,200,000 | 85,000,000 | -327,200,000 | -79.38% |
|    9 | Inverse Hybrid: Exponential Decay → Steiner (cov 3) | 412,200,000 | 78,500,000 | -333,700,000 | -80.96% |
|    10 | Inverse Hybrid: Markov Chain → Steiner (cov 3) | 412,200,000 | 76,500,000 | -335,700,000 | -81.44% |
|    11 | Inverse Hybrid: Pattern → Steiner (cov 3) | 412,200,000 | 75,500,000 | -336,700,000 | -81.68% |
|    12 | Inverse Hybrid: Not Repeat → Steiner (cov 3) | 412,200,000 | 73,500,000 | -338,700,000 | -82.17% |
|    13 | Inverse Hybrid: Cold Numbers → Steiner (cov 3) | 412,200,000 | 71,500,000 | -340,700,000 | -82.65% |
|    14 | Hybrid: Steiner + Exponential Decay | 412,200,000 | 60,600,000 | -351,600,000 | -85.30% |
|    15 | Hybrid: Steiner + Not Repeat | 412,200,000 | 59,000,000 | -353,200,000 | -85.69% |
|    16 | Hybrid: Steiner + Cold Numbers | 412,200,000 | 58,900,000 | -353,300,000 | -85.71% |


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
| Total gain | 181,650,000 VND |
| Net profit/loss | -230,550,000 VND |
| ROI | -55.93% |

#### Match Distribution
  - **5 matches**: 3 times
  - **4 matches**: 49 times
  - **3 matches**: 743 times
  - **2 matches**: 5,446 times
  - **1 matches**: 16,851 times
  - **0 matches**: 18,128 times

#### Best Results (5+ matches)
| date                | result                     | predicted             | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:----------------------|:--------------------|----------------:|--------------:|
| 2018-09-06 00:00:00 | [4, 11, 15, 21, 24, 27, 7] | [1, 4, 7, 15, 21, 24] |                     |               0 |             5 |
| 2017-12-23 00:00:00 | [7, 8, 9, 13, 28, 44, 12]  | [7, 8, 9, 11, 12, 13] |                     |               0 |             5 |
| 2017-12-23 00:00:00 | [7, 8, 9, 13, 28, 44, 12]  | [7, 8, 9, 11, 12, 13] |                     |               0 |             5 |

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
| Total gain | 140,300,000 VND |
| Net profit/loss | -271,900,000 VND |
| ROI | -65.96% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 42 times
  - **3 matches**: 786 times
  - **2 matches**: 5,453 times
  - **1 matches**: 16,734 times
  - **0 matches**: 18,203 times

#### Best Results (5+ matches)
| date                | result                       | predicted               | predicted_special   |   special_match |   correct_num |
|:--------------------|:-----------------------------|:------------------------|:--------------------|----------------:|--------------:|
| 2018-06-21 00:00:00 | [2, 8, 19, 23, 25, 33, 32]   | [2, 4, 8, 23, 25, 32]   |                     |               0 |             5 |
| 2017-09-14 00:00:00 | [22, 23, 32, 43, 44, 51, 15] | [3, 15, 23, 32, 43, 51] |                     |               0 |             5 |

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
| Total gain | 58,900,000 VND |
| Net profit/loss | -353,300,000 VND |
| ROI | -85.71% |

#### Match Distribution
  - **4 matches**: 43 times
  - **3 matches**: 748 times
  - **2 matches**: 5,426 times
  - **1 matches**: 16,653 times
  - **0 matches**: 18,350 times

#### Best Results (5+ matches)
No results with 5+ matches found.

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
| Total gain | 105,100,000 VND |
| Net profit/loss | -307,100,000 VND |
| ROI | -74.50% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 52 times
  - **3 matches**: 782 times
  - **2 matches**: 5,391 times
  - **1 matches**: 16,930 times
  - **0 matches**: 18,064 times

#### Best Results (5+ matches)
| date                | result                     | predicted             | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:----------------------|:--------------------|----------------:|--------------:|
| 2025-06-10 00:00:00 | [3, 6, 21, 29, 40, 41, 37] | [3, 5, 6, 21, 37, 41] |                     |               0 |             5 |

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
| Total gain | 59,000,000 VND |
| Net profit/loss | -353,200,000 VND |
| ROI | -85.69% |

#### Match Distribution
  - **4 matches**: 50 times
  - **3 matches**: 680 times
  - **2 matches**: 5,452 times
  - **1 matches**: 17,124 times
  - **0 matches**: 17,914 times

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
| Total gain | 60,600,000 VND |
| Net profit/loss | -351,600,000 VND |
| ROI | -85.30% |

#### Match Distribution
  - **4 matches**: 47 times
  - **3 matches**: 742 times
  - **2 matches**: 5,446 times
  - **1 matches**: 16,784 times
  - **0 matches**: 18,201 times

#### Best Results (5+ matches)
No results with 5+ matches found.

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
| Total gain | 180,950,000 VND |
| Net profit/loss | -231,250,000 VND |
| ROI | -56.10% |

#### Match Distribution
  - **5 matches**: 3 times
  - **4 matches**: 43 times
  - **3 matches**: 789 times
  - **2 matches**: 5,441 times
  - **1 matches**: 16,826 times
  - **0 matches**: 18,118 times

#### Best Results (5+ matches)
| date                | result                     | predicted             | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:----------------------|:--------------------|----------------:|--------------:|
| 2026-02-07 00:00:00 | [3, 5, 13, 15, 29, 46, 1]  | [1, 3, 5, 14, 15, 29] |                     |               0 |             5 |
| 2025-06-10 00:00:00 | [3, 6, 21, 29, 40, 41, 37] | [1, 3, 6, 21, 37, 41] |                     |               0 |             5 |
| 2023-11-11 00:00:00 | [2, 3, 4, 19, 41, 42, 23]  | [2, 3, 4, 23, 35, 42] |                     |               0 |             5 |

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
