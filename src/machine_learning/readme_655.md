# 🔮 Vietlott Power 655 Hybrid Prediction Summary

> **Generated**: 2026-07-24 17:33:09
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
| 🥇 1 | Inverse Hybrid: Markov Chain → Steiner (cov 3) | 412,200,000 | 30,150,550,000 | 29,738,350,000 | 7214.54% |
| 🥈 2 | Inverse Hybrid: Pattern → Steiner (cov 3) | 412,200,000 | 167,350,000 | -244,850,000 | -59.40% |
| 🥉 3 | Inverse Hybrid: Exponential Decay → Steiner (cov 3) | 412,200,000 | 152,550,000 | -259,650,000 | -62.99% |
|    4 | Inverse Hybrid: Not Repeat → Steiner (cov 3) | 412,200,000 | 150,400,000 | -261,800,000 | -63.51% |
|    5 | Inverse Hybrid: Pair Frequency → Steiner (cov 3) | 412,200,000 | 149,950,000 | -262,250,000 | -63.62% |
|    6 | Inverse Hybrid: Hot Numbers → Steiner (cov 3) | 412,200,000 | 149,850,000 | -262,350,000 | -63.65% |
|    7 | Inverse Hybrid: Cold Numbers → Steiner (cov 3) | 412,200,000 | 149,550,000 | -262,650,000 | -63.72% |
|    8 | Hybrid: Steiner + Hot Numbers | 412,200,000 | 141,900,000 | -270,300,000 | -65.57% |
|    9 | Hybrid: Steiner + Cold Numbers | 412,200,000 | 112,450,000 | -299,750,000 | -72.72% |
|    10 | Hybrid: Steiner + Long Absence | 412,200,000 | 106,900,000 | -305,300,000 | -74.07% |
|    11 | Inverse Hybrid: Long Absence → Steiner (cov 3) | 412,200,000 | 81,500,000 | -330,700,000 | -80.23% |
|    12 | Hybrid: Steiner + Exponential Decay | 412,200,000 | 68,150,000 | -344,050,000 | -83.47% |
|    13 | Hybrid: Steiner + Not Repeat | 412,200,000 | 64,350,000 | -347,850,000 | -84.39% |
|    14 | Hybrid: Steiner + Markov Chain | 412,200,000 | 63,300,000 | -348,900,000 | -84.64% |
|    15 | Hybrid: Steiner + Pair Frequency | 412,200,000 | 59,050,000 | -353,150,000 | -85.67% |
|    16 | Steiner Strategy | 412,200,000 | 56,800,000 | -355,400,000 | -86.22% |


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
| Total gain | 56,800,000 VND |
| Net profit/loss | -355,400,000 VND |
| ROI | -86.22% |

#### Match Distribution
  - **4 matches**: 46 times
  - **3 matches**: 676 times
  - **2 matches**: 5,466 times
  - **1 matches**: 17,250 times
  - **0 matches**: 17,782 times

#### Best Results (5+ matches)
No results with 5+ matches found.

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
| Total gain | 59,050,000 VND |
| Net profit/loss | -353,150,000 VND |
| ROI | -85.67% |

#### Match Distribution
  - **4 matches**: 39 times
  - **3 matches**: 791 times
  - **2 matches**: 5,700 times
  - **1 matches**: 17,107 times
  - **0 matches**: 17,583 times

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
| Total gain | 141,900,000 VND |
| Net profit/loss | -270,300,000 VND |
| ROI | -65.57% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 40 times
  - **3 matches**: 838 times
  - **2 matches**: 5,735 times
  - **1 matches**: 16,818 times
  - **0 matches**: 17,787 times

#### Best Results (5+ matches)
| date                | result                       | predicted                | predicted_special   |   special_match |   correct_num |
|:--------------------|:-----------------------------|:-------------------------|:--------------------|----------------:|--------------:|
| 2025-04-10 00:00:00 | [10, 13, 36, 37, 40, 43, 41] | [13, 20, 36, 37, 40, 41] |                     |               0 |             5 |
| 2023-07-04 00:00:00 | [4, 13, 14, 23, 33, 50, 41]  | [13, 14, 23, 33, 35, 41] |                     |               0 |             5 |

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
| Total gain | 112,450,000 VND |
| Net profit/loss | -299,750,000 VND |
| ROI | -72.72% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 60 times
  - **3 matches**: 849 times
  - **2 matches**: 5,547 times
  - **1 matches**: 17,164 times
  - **0 matches**: 17,599 times

#### Best Results (5+ matches)
| date                | result                     | predicted              | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:-----------------------|:--------------------|----------------:|--------------:|
| 2023-08-26 00:00:00 | [5, 8, 24, 38, 50, 51, 47] | [5, 8, 35, 38, 47, 51] |                     |               0 |             5 |

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
| Total gain | 106,900,000 VND |
| Net profit/loss | -305,300,000 VND |
| ROI | -74.07% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 53 times
  - **3 matches**: 808 times
  - **2 matches**: 5,680 times
  - **1 matches**: 17,147 times
  - **0 matches**: 17,531 times

#### Best Results (5+ matches)
| date                | result                      | predicted                | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:-------------------------|:--------------------|----------------:|--------------:|
| 2023-07-04 00:00:00 | [4, 13, 14, 23, 33, 50, 41] | [13, 14, 23, 33, 35, 41] |                     |               0 |             5 |

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
| Total gain | 64,350,000 VND |
| Net profit/loss | -347,850,000 VND |
| ROI | -84.39% |

#### Match Distribution
  - **4 matches**: 46 times
  - **3 matches**: 827 times
  - **2 matches**: 5,785 times
  - **1 matches**: 17,125 times
  - **0 matches**: 17,437 times

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
| Total gain | 68,150,000 VND |
| Net profit/loss | -344,050,000 VND |
| ROI | -83.47% |

#### Match Distribution
  - **4 matches**: 55 times
  - **3 matches**: 813 times
  - **2 matches**: 5,554 times
  - **1 matches**: 17,108 times
  - **0 matches**: 17,690 times

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
| Total gain | 63,300,000 VND |
| Net profit/loss | -348,900,000 VND |
| ROI | -84.64% |

#### Match Distribution
  - **4 matches**: 47 times
  - **3 matches**: 796 times
  - **2 matches**: 5,698 times
  - **1 matches**: 17,141 times
  - **0 matches**: 17,538 times

#### Best Results (5+ matches)
No results with 5+ matches found.

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
| Total gain | 149,950,000 VND |
| Net profit/loss | -262,250,000 VND |
| ROI | -63.62% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 49 times
  - **3 matches**: 909 times
  - **2 matches**: 5,910 times
  - **1 matches**: 16,633 times
  - **0 matches**: 17,717 times

#### Best Results (5+ matches)
| date                | result                      | predicted                | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:-------------------------|:--------------------|----------------:|--------------:|
| 2023-07-04 00:00:00 | [4, 13, 14, 23, 33, 50, 41] | [13, 14, 23, 28, 33, 41] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15]  | [3, 9, 15, 17, 23, 49]   |                     |               0 |             5 |

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
| Total gain | 149,850,000 VND |
| Net profit/loss | -262,350,000 VND |
| ROI | -63.65% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 49 times
  - **3 matches**: 907 times
  - **2 matches**: 5,920 times
  - **1 matches**: 16,606 times
  - **0 matches**: 17,736 times

#### Best Results (5+ matches)
| date                | result                      | predicted                | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:-------------------------|:--------------------|----------------:|--------------:|
| 2023-07-04 00:00:00 | [4, 13, 14, 23, 33, 50, 41] | [13, 14, 23, 28, 33, 41] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15]  | [3, 9, 15, 17, 23, 49]   |                     |               0 |             5 |

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
| Total gain | 149,550,000 VND |
| Net profit/loss | -262,650,000 VND |
| ROI | -63.72% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 49 times
  - **3 matches**: 901 times
  - **2 matches**: 5,782 times
  - **1 matches**: 16,848 times
  - **0 matches**: 17,638 times

#### Best Results (5+ matches)
| date                | result                      | predicted               | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:------------------------|:--------------------|----------------:|--------------:|
| 2018-08-16 00:00:00 | [6, 10, 34, 46, 48, 51, 47] | [6, 10, 28, 34, 47, 51] |                     |               0 |             5 |
| 2018-03-06 00:00:00 | [2, 6, 13, 22, 40, 48, 12]  | [6, 13, 22, 27, 40, 48] |                     |               0 |             5 |

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
| Total gain | 81,500,000 VND |
| Net profit/loss | -330,700,000 VND |
| ROI | -80.23% |

#### Match Distribution
  - **4 matches**: 65 times
  - **3 matches**: 980 times
  - **2 matches**: 5,765 times
  - **1 matches**: 16,465 times
  - **0 matches**: 17,945 times

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
| Total gain | 150,400,000 VND |
| Net profit/loss | -261,800,000 VND |
| ROI | -63.51% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 50 times
  - **3 matches**: 908 times
  - **2 matches**: 5,624 times
  - **1 matches**: 16,741 times
  - **0 matches**: 17,895 times

#### Best Results (5+ matches)
| date                | result                     | predicted              | predicted_special   |   special_match |   correct_num |
|:--------------------|:---------------------------|:-----------------------|:--------------------|----------------:|--------------:|
| 2018-09-13 00:00:00 | [4, 6, 7, 26, 40, 44, 9]   | [4, 7, 8, 9, 26, 44]   |                     |               0 |             5 |
| 2018-03-31 00:00:00 | [3, 7, 31, 43, 51, 53, 26] | [3, 7, 16, 26, 51, 53] |                     |               0 |             5 |

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
| Total gain | 152,550,000 VND |
| Net profit/loss | -259,650,000 VND |
| ROI | -62.99% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 60 times
  - **3 matches**: 851 times
  - **2 matches**: 6,074 times
  - **1 matches**: 16,875 times
  - **0 matches**: 17,358 times

#### Best Results (5+ matches)
| date                | result                      | predicted                | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:-------------------------|:--------------------|----------------:|--------------:|
| 2025-05-08 00:00:00 | [8, 14, 29, 37, 39, 50, 21] | [14, 21, 29, 37, 39, 51] |                     |               0 |             5 |
| 2023-07-04 00:00:00 | [4, 13, 14, 23, 33, 50, 41] | [13, 14, 23, 27, 41, 50] |                     |               0 |             5 |

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
| Total gain | 30,150,550,000 VND |
| Net profit/loss | 29,738,350,000 VND |
| ROI | 7214.54% |

#### Match Distribution
  - **6 matches**: 1 times
  - **5 matches**: 2 times
  - **4 matches**: 58 times
  - **3 matches**: 831 times
  - **2 matches**: 5,760 times
  - **1 matches**: 17,168 times
  - **0 matches**: 17,400 times

#### Best Results (5+ matches)
| date                | result                      | predicted               | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:------------------------|:--------------------|----------------:|--------------:|
| 2023-08-19 00:00:00 | [7, 9, 13, 22, 27, 42, 23]  | [9, 13, 22, 23, 27, 50] |                     |               0 |             5 |
| 2019-03-05 00:00:00 | [1, 15, 23, 51, 53, 55, 26] | [1, 15, 23, 49, 53, 55] |                     |               0 |             5 |
| 2018-12-25 00:00:00 | [3, 9, 17, 21, 23, 51, 15]  | [3, 9, 15, 17, 23, 51]  |                     |               0 |             6 |

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
| Total gain | 167,350,000 VND |
| Net profit/loss | -244,850,000 VND |
| ROI | -59.40% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 76 times
  - **3 matches**: 987 times
  - **2 matches**: 6,022 times
  - **1 matches**: 17,124 times
  - **0 matches**: 17,009 times

#### Best Results (5+ matches)
| date                | result                      | predicted               | predicted_special   |   special_match |   correct_num |
|:--------------------|:----------------------------|:------------------------|:--------------------|----------------:|--------------:|
| 2017-11-11 00:00:00 | [12, 26, 33, 35, 36, 44, 1] | [1, 26, 33, 35, 36, 51] |                     |               0 |             5 |
| 2017-11-11 00:00:00 | [12, 26, 33, 35, 36, 44, 1] | [1, 12, 22, 26, 35, 36] |                     |               0 |             5 |




---

## ⚠️ Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random and cannot be reliably predicted. Never gamble more than you can afford to lose.
