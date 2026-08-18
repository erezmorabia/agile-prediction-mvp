# Beating the Popularity Baseline — Investigation Summary

## Background

The production system recommends up to `top_n` agile practices for a team to
work on next, using a hybrid of collaborative filtering (similar teams) and
practice-transition sequences. Its headline result — **50.3% accuracy**,
tuned once via a 648-combination grid search on the full 10-month dataset —
was flagged by a professor review as methodologically circular: the same
data was used both to select the hyperparameters and to report the accuracy
(optimization bias).

This document summarizes everything explored so far in response to that
review, why it's harder to fix than it first appeared, and what's still
open.

## Dataset

- 10 months: `2020-01-07, 2020-03-04, 2020-04-02, 2020-05-03, 2020-06-08, 2020-07-05, 2020-08-03, 2020-09-06, 2020-10-05, 2020-11-04`
- 87 teams (2 excluded for having only 1 time period)
- 35 practices, 30 kept after dropping 5 with >90% missing values
- Rolling-window backtest requires ≥4 months of history; the earliest
  test point is `2020-05-03` (using months 1-3 as history), giving 7 test
  months total in a full backtest
- **`top_n` is a genuine operational constraint, not a tunable knob**: a team
  can realistically only work on 2 practices in parallel, so `top_n=2` is
  fixed throughout the analysis below unless noted otherwise

## Metric definitions

- **Accuracy (HR@N)**: per team/month, 1 if *any* of the `top_n` recommended
  practices was actually improved within a 3-month window (test month, +1,
  +2), else 0. Aggregated as the **mean of each month's own accuracy**
  (macro-average), not a single pooled count.
- **Random baseline**: probability of ≥1 hit by chance, given that month's
  own average improvements-per-team (`k_avg`) and `top_n`.
- **Popularity baseline**: always recommend the `top_n` practices that
  improved most often organization-wide (ignoring the target team's own
  state), learned only from months strictly before the test month —
  **verified leak-free** directly in `src/ml/sequences.py`
  (`learn_sequences_up_to_month` restricts to `months < max_month`, and the
  popularity counter is built from that same restricted set). This is a much
  tougher bar than random chance.

## The current "best" result and why it's not actually a clean win

The fixed config (`top_n=2, similarity_weight=0.7, k_similar=19,
min_similarity_threshold=0.75, lookahead=3, recent=3`) scores **50.3%**
accuracy overall, vs. an aggregate popularity baseline of **43.6%** — a
~1.15x margin. But broken down by month, this is **not** a month-by-month
win:

| Month | Accuracy | Popularity | Beats? |
|---|---|---|---|
| 2020-05-03 | 52.4% | 33.3% | **YES** |
| 2020-06-08 | 33.3% | 28.6% | **YES** |
| 2020-07-05 | 43.5% | 34.8% | **YES** |
| 2020-08-03 | 65.2% | 78.3% | no |
| 2020-09-06 | 38.5% | 42.3% | no |
| 2020-10-05 | 39.1% | 47.8% | no |
| 2020-11-04 | 80.0% | 40.0% | **YES** |

**4 of 7 months, not 7 of 7.** The aggregate win comes from a few strong
months (especially 2020-11-04 at 2.0x) outweighing losses in three
consecutive months (2020-08-03 through 2020-10-05) where popularity is
unusually dominant — those are months where a large share of teams improve
the same handful of practices simultaneously (avg. 3.6-5.1 practices
improved per team that stretch), leaving little room for per-team
personalization to add value over "follow the crowd."

## What's been tried to fix the optimization bias, and what happened

### 1. Single train/holdout split (tune once, evaluate once on genuinely
held-out months — the professor's literal suggestion)
- Tune on months 1-5, hold out months 6-10 (`top_n` unrestricted): held-out
  accuracy **48.3%** — close to 50.3%, but the winning config used `top_n=4`,
  violating the real constraint.
- Same idea with `top_n=2` fixed, tune on 1-5 / hold out 5: **35.4%**
- Tune on 1-7 / hold out 3: **31.9%** (unreliable — 3-month holdout is too
  small a sample; using the *original* fixed config on those same 3 months
  scores 52.5%, showing the holdout size alone swings results by 20+ points)

### 2. Month-by-month walk-forward re-tuning (no future leak: at each step,
tune only on prior months, then predict the next single month)
- First attempt had a **methodology bug**: the outer evaluation truncated
  the dataset at the predict-month, which silently shrunk the 3-month
  validation window to ~1 month for every step except the last, undercounting
  hits. Fixed by evaluating against the full dataset while keeping the
  *tuning* step properly restricted to prior months only.
- After the fix, with `top_n=2` fixed and a 162-combination grid:
  **40.8% aggregate accuracy vs. 44.5% aggregate popularity** — loses in
  aggregate, and only the 3 non-retuned "bootstrap" months (which use the
  fixed config as a fallback, since there's too little history to tune yet)
  beat popularity. All 4 genuinely re-tuned months lose.

### 3. Does the selection criterion matter? (`improvement_gap` vs. random,
which `OptimizationEngine` has always used, vs. `popularity_gap`, which
directly targets what we actually want to beat)
- Re-ran the walk-forward loop selecting each step's winner by
  `popularity_gap` instead. **Identical results in every single step** — the
  two criteria always picked the same config. On a small inner tuning
  sample, both are just "accuracy minus a roughly month-constant baseline,"
  so they rank candidates the same way. **The selection criterion was never
  the actual problem.**

### 4. Does a wider parameter grid help? (oracle check first, then a
legitimate re-run)
- An **oracle diagnostic** — checking every candidate directly against the
  *real, already-known* outcome for each hard month (not a legitimate
  forecasting process, but a ceiling check) — found:
  - 2020-08-03: 0/162 beat popularity even in a much wider 1890-combo grid
    (best 1.06x, needs `min_similarity_threshold=0.0`)
  - 2020-09-06: 0/1890 beat popularity even with the wide grid — best is an
    exact tie, **zero improvement** from an 11.7x larger search
  - 2020-10-05: 342/1890 beat popularity, up to 2.0x (needs `min_sim=0.6`)
  - This showed the ceiling is **data-dependent per month**, not a search
    coverage problem — for some months no config in a very wide space wins;
    for others many do.
- Re-ran the **legitimate** (no-leak) version with progressively larger,
  targeted grids:

| Grid size | Aggregate accuracy | Aggregate popularity |
|---|---|---|
| 162 (original) | 40.8% | 44.5% |
| 324 (+ `sim_weight=0.5`, `min_sim=0.0`) | 42.0% | 44.5% |
| 432 (+ `min_sim=0.6`) | 42.0% (no change) | 44.5% |
| 1890 (full wide grid) | 42.6% | 44.5% |

  Clear diminishing returns: even though the wider grids *contained* the
  exact values the oracle showed were needed, the legitimate (past-data-only)
  tuning step usually didn't select them — because "best fit on the last 3-9
  months" and "best fit on the next unseen month" are different things, and
  a 3-6 month sample isn't enough to tell them apart.

### 5. "Semi-fixed": bootstrap with the fixed config, tune once after a few
months, then freeze that config for the rest
- Checked whether tuning on an early subset (5, 6, 7, 8, or **9** of the 10
  months) ever recovers the original fixed config's parameters: **no, not
  even close, at any subset size** — best match is 2 of 5 parameters, even
  using 9 of 10 months.
- Checked whether the config found at 9 months (frozen for the final month)
  beats popularity there: **no** — 33.3% vs. 50.0%, not the fixed config's
  80.0%.
- This idea is structurally identical to the single-split experiments in
  §1, which already underperformed even the noisy monthly re-tuning
  approach.

## Core finding

**No legitimate (no-future-leak) approach tried so far — single split,
monthly re-tuning, any grid size from 162 to 1890 combinations, either
selection criterion, or bootstrap-then-freeze — beats the popularity
baseline in aggregate.** The best achieved is 42.6% vs. 44.5% (1890-combo
walk-forward). Only the original, circular, tuned-on-all-7-test-months fixed
config manages an aggregate win (50.3% vs. 43.6%), and even that loses
outright in 3 of 7 individual months. Popularity's strength in those months
is verified to be leak-free — it reflects a real property of the data
(highly correlated team behavior in certain stretches), not a measurement
artifact.

## Goal

Find a **month-by-month (walk-forward, no future leak) or semi-fixed-config
approach** that beats the popularity baseline **in aggregate** across the
available months — matching the standard the current (circular) fixed
config meets, but via a methodology that doesn't require seeing the months
it's evaluated on.

## Ideas not yet tried

- A **hybrid/adaptive** approach: detect months or situations where team
  behavior is highly correlated (e.g., via `k_avg` or another
  convergence signal) and fall back to pure popularity there, using the
  personalized model only when there's genuine team-to-team divergence to
  exploit.
- **Ensembling** the personalized model's recommendations with popularity's
  (e.g., blend scores, or recommend 1 personalized + 1 popular practice when
  `top_n=2`) rather than treating them as competing, mutually exclusive
  strategies.
- A **more robust inner-selection rule** than "pick the single highest
  inner-accuracy config" — e.g., requiring consistent performance across
  *all* inner test points rather than the best average, to reduce sensitivity
  to small-sample noise.
- Re-examining whether **more historical data** (more months, if available)
  would give the walk-forward approach's inner tuning enough evidence per
  step to close the gap — the diminishing-but-nonzero returns from grid
  expansion suggest sample size, not grid coverage, is the binding
  constraint.
