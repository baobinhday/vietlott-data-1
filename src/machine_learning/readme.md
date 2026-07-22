# Vietlott Power 655 Prediction Summary

> **Generated**: 2026-07-22 15:14:27
>
> This document contains machine learning predictions for Vietnamese lottery data.
> This is an experimental module for educational purposes only.

## Strategy Performance Comparison

> Sorted by ROI (best → worst).  All strategies backtested with **30 tickets/draw**.
> Note: All ROIs are deeply negative — lottery odds make profit impossible at scale.
> The comparison shows *which strategy loses the least*, not which one is profitable.

| Rank | Strategy | Total Cost (VND) | Total Gain (VND) | Net Profit (VND) | ROI |
|------|----------|-----------------|-----------------|-----------------|-----|
| 🥇 1 | Pair Frequency Strategy | 412,200,000 | 15,074,300,000 | 14,662,100,000 | 3557.04% |
| 🥈 2 | Pattern Strategy | 412,200,000 | 15,066,350,000 | 14,654,150,000 | 3555.11% |
| 🥉 3 | Not Repeat Strategy | 412,200,000 | 10,079,950,000 | 9,667,750,000 | 2345.40% |
|    4 | Random Strategy | 412,200,000 | 10,074,200,000 | 9,662,000,000 | 2344.01% |
|    5 | Markov Chain Strategy | 412,200,000 | 5,080,050,000 | 4,667,850,000 | 1132.42% |
|    6 | Cold Numbers Strategy | 412,200,000 | 5,076,350,000 | 4,664,150,000 | 1131.53% |
|    7 | Hot Numbers Strategy | 412,200,000 | 5,074,650,000 | 4,662,450,000 | 1131.11% |
|    8 | Exponential Decay Strategy | 412,200,000 | 5,070,350,000 | 4,658,150,000 | 1130.07% |
|    9 | Steiner Strategy | 412,200,000 | 5,065,500,000 | 4,653,300,000 | 1128.89% |
|    10 | Long Absence Strategy | 412,200,000 | 81,350,000 | -330,850,000 | -80.26% |


## Strategy Descriptions

### Random Strategy

**How it works**: Generates tickets by shuffling all numbers in the valid range and picking the first `number_predict` entries.  Every number has an equal chance of being selected; no historical data is used.

**Use case**: Serves as an unbiased performance baseline.  Any strategy that cannot beat random selection over a large backtest offers no predictive value.

### Long Absence Strategy

**How it works**: For each draw date, looks back at all past draws and records the last date each number appeared.  Numbers are ranked by how many days have elapsed since they last appeared (numbers that have *never* appeared rank highest). A configurable pool of the `top_n` most-absent numbers is assembled, and `number_predict` numbers are randomly sampled from that pool.

**Key parameter**: `top_n` (default 10) – larger pool → more randomness; smaller pool → stronger bias toward the longest-absent numbers.

**Use case**: Captures the intuition that numbers that have been *overdue* for a long time are somehow more likely to appear.  (Note: for a fair lottery this intuition is mathematically incorrect, but the strategy is included for empirical comparison.)

### Pattern Strategy

**How it works**: Analyses two structural properties of historical draws in a rolling `lookback_days` window:

1. **Spacing patterns** – gaps between consecutive sorted numbers in a ticket.  The most common gaps are used to generate the next number by applying a sampled gap to the previously chosen number.
2. **Range distribution** – the number range 1–55 is split into five equal sub-ranges.  The historical fraction of draws falling in each sub-range is used as a probability weight for choosing the first number.

A `pattern_weight` fraction of the ticket is filled with pattern-derived numbers; the remainder is filled randomly.

**Key parameters**: `lookback_days` (default 180), `pattern_weight` (default 0.6).

### Hot Numbers Strategy

**How it works**: Counts how many times each number appeared over the last `lookback_days` days.  Numbers are sorted from most-frequent to least-frequent.  A weighted pool is built where each number is repeated proportionally to its frequency, then numbers are drawn without replacement from that pool.

A `selection_weight` fraction of the ticket is filled from the frequency-weighted pool; the rest is filled uniformly at random.

**Key parameters**: `lookback_days` (default 365), `selection_weight` (default 0.7).

**Use case**: Tests whether recently hot numbers continue to appear at above-average rates.

### Cold Numbers Strategy

**How it works**: Identical to Hot Numbers Strategy but ranks numbers in the *reverse* order (least frequent first).  The weighted pool gives higher weight to numbers that have appeared fewer times in the lookback window.

**Key parameters**: `lookback_days` (default 365), `selection_weight` (default 0.7).

**Use case**: Tests the complementary hypothesis that rarely-drawn numbers are more likely to appear (mean-reversion / gambler's fallacy).

### Not Repeat Strategy

**How it works**: Collects all numbers that appeared in *any* draw within the last `lookback_days` days.  Whenever enough *non-recent* numbers exist to fill a full ticket they are sampled uniformly.  When the pool of non-recent numbers is too small, remaining slots are filled using an `avoid_weight` probability to decide whether to pick from recent numbers or from the full range.

**Key parameters**: `lookback_days` (default 30), `avoid_weight` (default 0.8).

**Use case**: Models the idea that numbers drawn recently are *less* likely to repeat in the very next draw.

### Exponential Decay Strategy

**How it works**: Every historical draw contributes a score to each number it contained, but the contribution decays exponentially with age: ``weight = exp(-ln(2) × days_ago / half_life_days)``.  Draws from yesterday contribute much more than draws from a year ago.  Numbers are then selected from a pool weighted by their accumulated scores.

Unlike Hot/Cold Numbers Strategy there is **no hard window cutoff** — all history is used, with very old draws contributing negligibly.  The smooth decay avoids abrupt weight changes when a draw ages past a window boundary.

**Key parameters**: `half_life_days` (default 90), `hot` (default True), `selection_weight` (default 0.8).

### Pair Frequency Strategy

**How it works**: Builds a co-occurrence matrix from historical draws: ``cooccurrence[a][b]`` counts draws where numbers ``a`` and ``b`` both appeared.  Tickets are assembled iteratively:

1. The first number is sampled proportional to individual draw frequency.
2. Each subsequent number is sampled proportional to its **average co-occurrence score** with the numbers already selected.

This produces clusters of numbers that historically appear together, exploiting second-order correlations that all single-number strategies ignore.

**Key parameter**: `lookback_days` (default 365).

### Markov Chain Strategy

**How it works**: Models **first-order sequential dependencies** between consecutive draws — a dimension completely ignored by every other strategy.

A transition matrix ``T[a][b]`` is built from the lookback window: ``T[a][b]`` counts the number of times number ``a`` appeared in draw ``t`` **and** number ``b`` appeared in the *next* draw ``t+1``.  This captures cross-draw temporal correlations.

To predict for date ``d``:

1. Identify the most-recent draw before ``d`` — this is the **Markov state**.
2. For each candidate number ``n``, compute an aggregate score by summing ``T[s][n]`` over every number ``s`` in the state draw.
3. Sample ``number_predict`` numbers without replacement, weighted by (score + Laplace smoothing) to retain a non-zero chance for all numbers.

**Key parameters**: `lookback_days` (default 365), `smoothing` (default 0.5).

**Why this is novel**: Unlike Pair Frequency Strategy (which counts numbers that appear *together in the same draw*), Markov Chain counts numbers that appeared in *successive draws*.  If any temporal autocorrelation exists in the physical lottery mechanism, this strategy is best positioned to exploit it.


## Usage Examples

The strategies can be used independently outside this generator script.
Below are minimal runnable examples using Power 6/55 data.

### Install & load data

```python
import polars as pl
from vietlott.config.products import get_config

df_pl = pl.read_ndjson(get_config("power_655").raw_path)
df_pl = df_pl.with_columns(pl.col("date").str.to_date(strict=False))
df_pd = df_pl.to_pandas()
```

### Random baseline

```python
from machine_learning.strategies import RandomModel

model = RandomModel(df_pd, time_predict=5)
model.backtest()
model.evaluate()
cost, gain, profit = model.revenue()
print(f"ROI: {profit / cost * 100:.2f}%")
```

### Hot Numbers (frequency-based)

```python
from machine_learning.strategies import HotNumbersStrategy

model = HotNumbersStrategy(df_pd, time_predict=5, lookback_days=180, selection_weight=0.8)
model.backtest()
model.evaluate()
# Predict for a specific date
from datetime import date
print(model.predict(date(2025, 6, 1)))
```

### Markov Chain (sequential dependency)

```python
from machine_learning.strategies import MarkovChainStrategy

model = MarkovChainStrategy(df_pd, time_predict=5, lookback_days=365, smoothing=0.5)
model.backtest()
model.evaluate()
cost, gain, profit = model.revenue()
print(f"ROI: {profit / cost * 100:.2f}%")
```

### Backtest with a date range

```python
from machine_learning.strategies import PairFrequencyStrategy
from datetime import date

model = PairFrequencyStrategy(df_pd, time_predict=10, lookback_days=365)
# Only evaluate predictions for 2024 draws; full history is still used for lookups
model.backtest(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31))
model.evaluate()
cost, gain, profit = model.revenue()
print(f"2024 ROI: {profit / cost * 100:.2f}%")
```

### Compare strategies head-to-head

```python
from machine_learning.strategies import (
    RandomModel, MarkovChainStrategy, PairFrequencyStrategy,
)

strategies = {
    "Random":       RandomModel(df_pd, time_predict=20),
    "Markov":       MarkovChainStrategy(df_pd, time_predict=20),
    "PairFreq":     PairFrequencyStrategy(df_pd, time_predict=20),
}

for name, model in strategies.items():
    model.backtest()
    model.evaluate()
    cost, gain, profit = model.revenue()
    print(f"{name:20s}  ROI={profit / cost * 100:+.1f}%")
```


## Prediction Models

> **Disclaimer**: These are experimental models for educational purposes only. Lottery outcomes are random and cannot be predicted reliably.

### Random Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Random Strategy |
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
| Total gain | 10,074,200,000 VND |
| Net profit/loss | 9,662,000,000 VND |
| ROI | 2344.01% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 65 times
  - **3 matches**: 834 times
  - **2 matches**: 5,851 times
  - **1 matches**: 17,133 times
  - **0 matches**: 17,335 times

#### Best Results (5+ matches)
| date                | result                       | predicted               |   correct_num |
|:--------------------|:-----------------------------|:------------------------|--------------:|
| 2025-07-08 00:00:00 | [23, 24, 32, 42, 48, 50, 31] | [1, 23, 24, 31, 32, 50] |             5 |
| 2023-07-27 00:00:00 | [3, 11, 13, 31, 33, 45, 27]  | [3, 14, 27, 31, 33, 45] |             5 |

### Long Absence Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Long Absence Strategy |
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
| Total gain | 81,350,000 VND |
| Net profit/loss | -330,850,000 VND |
| ROI | -80.26% |

#### Match Distribution
  - **4 matches**: 71 times
  - **3 matches**: 917 times
  - **2 matches**: 5,849 times
  - **1 matches**: 16,715 times
  - **0 matches**: 17,668 times

#### Best Results (5+ matches)
No results with 5+ matches found.

### Pattern Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Pattern Strategy |
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
| Total gain | 15,066,350,000 VND |
| Net profit/loss | 14,654,150,000 VND |
| ROI | 3555.11% |

#### Match Distribution
  - **5 matches**: 3 times
  - **4 matches**: 47 times
  - **3 matches**: 857 times
  - **2 matches**: 5,856 times
  - **1 matches**: 16,921 times
  - **0 matches**: 17,536 times

#### Best Results (5+ matches)
| date                | result                     | predicted               |   correct_num |
|:--------------------|:---------------------------|:------------------------|--------------:|
| 2024-11-05 00:00:00 | [9, 31, 36, 46, 49, 54, 7] | [7, 30, 31, 36, 49, 54] |             5 |
| 2024-07-11 00:00:00 | [1, 2, 11, 21, 22, 23, 26] | [1, 11, 21, 22, 23, 37] |             5 |
| 2022-11-24 00:00:00 | [4, 6, 18, 27, 52, 53, 10] | [4, 6, 10, 18, 27, 40]  |             5 |

### Hot Numbers Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Hot Numbers Strategy |
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
| Total gain | 5,074,650,000 VND |
| Net profit/loss | 4,662,450,000 VND |
| ROI | 1131.11% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 62 times
  - **3 matches**: 873 times
  - **2 matches**: 5,726 times
  - **1 matches**: 17,049 times
  - **0 matches**: 17,509 times

#### Best Results (5+ matches)
| date                | result                       | predicted                |   correct_num |
|:--------------------|:-----------------------------|:-------------------------|--------------:|
| 2018-12-15 00:00:00 | [14, 17, 49, 52, 53, 55, 12] | [14, 38, 49, 52, 53, 55] |             5 |

### Cold Numbers Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Cold Numbers Strategy |
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
| Total gain | 5,076,350,000 VND |
| Net profit/loss | 4,664,150,000 VND |
| ROI | 1131.53% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 68 times
  - **3 matches**: 847 times
  - **2 matches**: 5,942 times
  - **1 matches**: 16,975 times
  - **0 matches**: 17,387 times

#### Best Results (5+ matches)
| date                | result                       | predicted                |   correct_num |
|:--------------------|:-----------------------------|:-------------------------|--------------:|
| 2022-12-13 00:00:00 | [10, 22, 31, 37, 41, 52, 20] | [10, 20, 31, 38, 41, 52] |             5 |

### Not Repeat Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Not Repeat Strategy |
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
| Total gain | 10,079,950,000 VND |
| Net profit/loss | 9,667,750,000 VND |
| ROI | 2345.40% |

#### Match Distribution
  - **5 matches**: 2 times
  - **4 matches**: 65 times
  - **3 matches**: 949 times
  - **2 matches**: 5,796 times
  - **1 matches**: 16,877 times
  - **0 matches**: 17,531 times

#### Best Results (5+ matches)
| date                | result                      | predicted               |   correct_num |
|:--------------------|:----------------------------|:------------------------|--------------:|
| 2023-03-21 00:00:00 | [7, 17, 31, 43, 45, 49, 52] | [7, 17, 37, 45, 49, 52] |             5 |
| 2021-09-18 00:00:00 | [3, 14, 15, 21, 47, 52, 54] | [3, 15, 21, 49, 52, 54] |             5 |

### Exponential Decay Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Exponential Decay Strategy |
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
| Total gain | 5,070,350,000 VND |
| Net profit/loss | 4,658,150,000 VND |
| ROI | 1130.07% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 56 times
  - **3 matches**: 847 times
  - **2 matches**: 5,864 times
  - **1 matches**: 17,119 times
  - **0 matches**: 17,333 times

#### Best Results (5+ matches)
| date                | result                       | predicted                |   correct_num |
|:--------------------|:-----------------------------|:-------------------------|--------------:|
| 2019-01-05 00:00:00 | [10, 11, 38, 47, 53, 55, 51] | [10, 11, 32, 51, 53, 55] |             5 |

### Pair Frequency Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Pair Frequency Strategy |
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
| Total gain | 15,074,300,000 VND |
| Net profit/loss | 14,662,100,000 VND |
| ROI | 3557.04% |

#### Match Distribution
  - **5 matches**: 3 times
  - **4 matches**: 62 times
  - **3 matches**: 866 times
  - **2 matches**: 5,775 times
  - **1 matches**: 17,031 times
  - **0 matches**: 17,483 times

#### Best Results (5+ matches)
| date                | result                       | predicted                |   correct_num |
|:--------------------|:-----------------------------|:-------------------------|--------------:|
| 2024-11-09 00:00:00 | [11, 14, 24, 26, 34, 51, 40] | [11, 14, 15, 24, 40, 51] |             5 |
| 2024-11-02 00:00:00 | [2, 9, 19, 20, 34, 54, 26]   | [2, 14, 19, 26, 34, 54]  |             5 |
| 2019-02-26 00:00:00 | [8, 9, 16, 34, 42, 43, 45]   | [8, 9, 34, 42, 45, 55]   |             5 |

### Markov Chain Strategy

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | Markov Chain Strategy |
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
| Total gain | 5,080,050,000 VND |
| Net profit/loss | 4,667,850,000 VND |
| ROI | 1132.42% |

#### Match Distribution
  - **5 matches**: 1 times
  - **4 matches**: 73 times
  - **3 matches**: 871 times
  - **2 matches**: 5,595 times
  - **1 matches**: 17,160 times
  - **0 matches**: 17,520 times

#### Best Results (5+ matches)
| date                | result                     | predicted              |   correct_num |
|:--------------------|:---------------------------|:-----------------------|--------------:|
| 2021-08-31 00:00:00 | [7, 20, 37, 47, 51, 53, 5] | [3, 7, 37, 47, 51, 53] |             5 |

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
| Total gain | 5,065,500,000 VND |
| Net profit/loss | 4,653,300,000 VND |
| ROI | 1128.89% |

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




---

## Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random and cannot be reliably predicted. Never gamble more than you can afford to lose.
