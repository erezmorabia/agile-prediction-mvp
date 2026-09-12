---
name: domain-validation
description: Rolling window backtest of the global two-month adaptive blend, primary/sensitivity aggregation, rank-aware metrics. Use when modifying backtest logic, the evaluable cohort, or random/popularity baseline formulas.
---

# Domain: Validation

## Summary
`BacktestEngine` validates the global two-month adaptive blend (owned by `PolicyEngine`, see `/domain-ml`) using a rolling window over every prediction month. There is no static parameter optimizer — it was removed entirely (engine, endpoints, web/CLI controls, skill) because the monthly policy selection is now the sole configuration authority.

## Data Flows

- **Backtest:** `BacktestEngine.run_backtest()` → for each month in `PolicyEngine.prediction_months()`: `evaluable_cases(month)` (fixed cohort, before any policy scoring) → `select_policy(month)` (the blend) and `select_popularity_arm(month)` (independent comparison arm) → scores every case under both policies → accumulates accuracy, precision@N, recall@N, MRR per month
- **Primary vs sensitivity split:** `per_month_results` covers every prediction month; `primary` aggregates only months where `PolicyEngine.full_outcome_window(month)` is true (complete 3-snapshot outcome window against the dataset's end); `sensitivity` aggregates all months. The two are never mixed
- **No results persistence:** unlike the deleted optimizer, backtest results are not saved to `results/*.json` — they are returned directly in the API response

## Domain Validation Rules and Business Logic

- Prediction months = `PolicyEngine.prediction_months()` (global index 3+); a month needs at least 4 total months of data to have any prediction months at all
- Evaluable cohort per month is fixed **before** any policy is scored, and is identical for every one of the 675 candidate policies and both reported arms (blend and popularity) — see `PolicyEngine.evaluable_cases()` in `/domain-ml`
- A case is evaluable when: it is recommendable (baseline exists, ≥2 candidate practices) AND at least one practice improved in the 3-snapshot outcome window after baseline
- Since every evaluable case is by construction recommendable, `BacktestEngine` never needs to catch a "can't recommend" exception per case — `PolicyEngine.recommend()`/`top_practices()` cannot raise for a cohort member

## Formulas / Scoring / Calculation Logic

**Overall accuracy (HR@N, i.e. Hit Rate@N / Success@N):** binary per case — 1 if *any* recommended
practice is in `actual_improved`, else 0.
```
overall_accuracy = mean(per_month_accuracy for each month in scope)
```

**Random baseline for HR@N** (probability of ≥1 correct recommendation by chance):
```
case_baseline(i)  = 1 − C(n_i − k_i, draws_i) / C(n_i, draws_i)
month_baseline(m) = mean(case_baseline(i) for each case i in month m)
random_baseline   = mean(month_baseline(m) for each month in scope)
```
- `n_i` = number of practices eligible for recommendation in case `i`
- `k_i` = number of those eligible candidates that improved, `top_n` = 2 (`policy.TOP_N`), and `draws_i = min(top_n, n_i)`
- `BacktestEngine._expected_random_hit_rate()` computes the exact per-case probability; invalid inputs or combination errors return 0.0
- Case probabilities are averaged within month, then macro-averaged across months — the same aggregation `overall_accuracy` uses — so the two are directly comparable

**Improvement factor:** `overall_accuracy / random_baseline`

### Supplementary rank-aware metrics (precision@N, recall@N, MRR)

Same as before the blend refactor — unchanged formulas, still computed per scope (primary/sensitivity) instead of one pooled run:

```
precision@N (case) = hits / top_n                       # MetricsCalculator.calculate_hit_rate
recall@N (case)    = hits / |actual_improved|            # hits / k for that case
mrr (case)         = 1 / rank of first hit, else 0        # MetricsCalculator.calculate_mrr
```

**Random baselines** — each metric needs its own chance-level comparison:
```
random_precision(i) = k_i / n_i
random_recall(i)    = min(top_n, n_i) / n_i
random_mrr          = mean(expected_mrr_per_case)
```
Each baseline is computed per case, averaged within month, and then macro-averaged across months. `random_mrr` uses `BacktestEngine._expected_random_mrr(n_i, k_i, top_n)` per case (negative hypergeometric rank distribution), rather than deriving it from an average improvement count.

**Two caveats when reading these numbers:**
- Recall@N is capped at `top_n / |actual_improved|` by construction.
- Precision@N equals HR@N only when `top_n=1`; at `top_n=2`, 1-of-2 correct scores HR@N=1.0 but precision@N=0.5.

### Time-aware popularity comparison arm (replaces the old static popularity baseline)

Independently selected each month under the same walk-forward rule as the blend, restricted to the 5 pure-popularity policies (0% similarity, 0% sequence — `POPULARITY_ARM_POLICIES` in `/domain-ml`), tie-broken by lower recency. Computed on **exactly the same evaluable cases** as the blend for that month — this is the fix for the old static popularity baseline, which used a fixed heuristic rather than a properly time-aware, walk-forward-selected comparison.

```
time_aware_popularity_accuracy = mean(per_month popularity-arm hit-rate)
blend_minus_popularity = accuracy - time_aware_popularity_accuracy
```

On the reference dataset (primary, 5 full-outcome-window months): blend 57.98% vs time-aware popularity 55.66% (+2.31pp). `tests/test_blend_reproduction.py` pins the per-month and aggregate reproduction values. This is exploratory, not a claim of proven superiority; three of the five primary months run on the bootstrap policy, where the blend is the popularity arm and the two tie exactly.

**Determinism note:** `PolicyEngine.top_practices()`'s final ranking is tie-broken deterministically by practice name, and `_preference_key()`'s monthly-policy-selection tie-break is a strict total order — both are reproducible across runs regardless of hash seed.

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `BacktestEngine.__init__()` | `src/validation/backtest.py` | `APIService`, CLI | `recommender_engine, processor` → also stores `self.policy_engine = recommender_engine.policy_engine` |
| `BacktestEngine.run_backtest()` | `src/validation/backtest.py` | `APIService.run_backtest()`, CLI `_validate_recommendations()` | no params → `{status, per_month_results, primary, sensitivity}` — no config dict, no `train_ratio` |
| `BacktestEngine._score_month()` | `src/validation/backtest.py` | `run_backtest()` | one prediction month → `(row, case_stats)`, where each case stat is `(eligible_candidate_count, improved_candidate_count)` |
| `BacktestEngine._aggregate_scope()` | `src/validation/backtest.py` | `run_backtest()` (primary and sensitivity, and any empty scope) | replaces the old duplicated `_build_partial_results()` — one aggregation function used for every scope |
| `BacktestEngine._expected_random_mrr()` | `src/validation/backtest.py` | `_score_month()` (per case) | staticmethod; `n, k, top_n` → exact expected MRR under random selection |
| `BacktestEngine._expected_random_hit_rate()` | `src/validation/backtest.py` | `_aggregate_scope()` (per case) | staticmethod; `n, k, top_n` → exact P(≥1 correct by chance) from the case's eligible candidate pool |

## Cross-references
- **Related Use Case Skills:** `/uc-02-run-backtest-validation`
- **Related Domain Skills:** `/domain-ml` (`PolicyEngine` owns the cohort, selection, and scoring that `BacktestEngine` replays), `/domain-api` (routes expose the backtest endpoint)
