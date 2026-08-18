---
name: domain-validation
description: Rolling window backtest of the global two-month adaptive blend, primary/sensitivity aggregation, rank-aware metrics, cancellation. Use when modifying backtest logic, the evaluable cohort, random/popularity baseline formulas, or the cancel mechanism.
---

# Domain: Validation

## Summary
`BacktestEngine` validates the global two-month adaptive blend (owned by `PolicyEngine`, see `/domain-ml`) using a rolling window over every prediction month. There is no static parameter optimizer — it was removed entirely (engine, endpoints, web/CLI controls, skill) because the monthly policy selection is now the sole configuration authority. `BacktestEngine` keeps its own `_cancelled` flag / `cancel()` / `reset_cancellation()`, moved over from the deleted optimizer.

## Data Flows

- **Backtest:** `BacktestEngine.run_backtest()` → resets `_cancelled` (a prior `cancel()` call must not silently cancel a fresh run) → for each month in `PolicyEngine.prediction_months()`: `evaluable_cases(month)` (fixed cohort, before any policy scoring) → `select_policy(month)` (the blend) and `select_popularity_arm(month)` (independent comparison arm) → scores every case under both policies → accumulates accuracy, precision@N, recall@N, MRR per month
- **Primary vs sensitivity split:** `per_month_results` covers every prediction month; `primary` aggregates only months where `PolicyEngine.full_outcome_window(month)` is true (complete 3-snapshot outcome window against the dataset's end); `sensitivity` aggregates all months. The two are never mixed
- **Cancellation:** `cancellation_check` callable (or `self._cancelled` if none passed) is polled at the top of each month and every 10 cases within a month; on trip, the in-progress month is dropped entirely (not partially included) and the run returns with `cancelled: True`. `POST /api/backtest/cancel` → `APIService.cancel_backtest()` → `BacktestEngine.cancel()`
- **No results persistence:** unlike the deleted optimizer, backtest results are not saved to `results/*.json` — they are returned directly in the API response

## Domain Validation Rules and Business Logic

- Prediction months = `PolicyEngine.prediction_months()` (global index 3+); a month needs at least 4 total months of data to have any prediction months at all
- Evaluable cohort per month is fixed **before** any policy is scored, and is identical for every one of the 675 candidate policies and both reported arms (blend and popularity) — see `PolicyEngine.evaluable_cases()` in `/domain-ml`
- A case is evaluable when: it is recommendable (baseline exists, ≥2 candidate practices) AND at least one practice improved in the 3-snapshot outcome window after baseline
- Since every evaluable case is by construction recommendable, `BacktestEngine` never needs to catch a "can't recommend" exception per case — `PolicyEngine.recommend()`/`top_practices()` cannot raise for a cohort member
- `cancellation_check` is polled every 10 cases within a month's team loop, and once at the start of each month

## Formulas / Scoring / Calculation Logic

**Overall accuracy (HR@N, i.e. Hit Rate@N / Success@N):** binary per case — 1 if *any* recommended
practice is in `actual_improved`, else 0.
```
overall_accuracy = mean(per_month_accuracy for each month in scope)
```

**Random baseline for HR@N** (probability of ≥1 correct recommendation by chance):
```
month_baseline(m) = 1 − C(n − k_avg(m), top_n) / C(n, top_n)   # BacktestEngine._baseline_from_k_avg
random_baseline    = mean(month_baseline(m) for each month in scope)
```
- `n` = total number of practices, `top_n` = 2 (`policy.TOP_N`)
- `k_avg(m)` = average number of improvements per case, within month `m` only
- Falls back to `min(1.0, (k_avg / n) * top_n)` if combination calculation fails
- `random_baseline` is macro-averaged per month — the same aggregation `overall_accuracy` uses — so the two are directly comparable

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
random_precision = k_avg / n     # exact, linear in k
random_recall    = top_n / n     # exact, doesn't depend on k
random_mrr       = mean(expected_mrr_per_case)   # NOT derived from k_avg — nonlinear in k
```
`random_mrr` uses `BacktestEngine._expected_random_mrr(n, k, top_n)` per case (negative hypergeometric rank distribution), averaged — not derived from `k_avg`.

**Two caveats when reading these numbers:**
- Recall@N is capped at `top_n / |actual_improved|` by construction.
- Precision@N equals HR@N only when `top_n=1`; at `top_n=2`, 1-of-2 correct scores HR@N=1.0 but precision@N=0.5.

### Time-aware popularity comparison arm (replaces the old static popularity baseline)

Independently selected each month under the same walk-forward rule as the blend, restricted to the 5 pure-popularity policies (0% similarity, 0% sequence — `POPULARITY_ARM_POLICIES` in `/domain-ml`), tie-broken by lower recency. Computed on **exactly the same evaluable cases** as the blend for that month — this is the fix for the old static popularity baseline, which used a fixed heuristic rather than a properly time-aware, walk-forward-selected comparison.

```
time_aware_popularity_accuracy = mean(per_month popularity-arm hit-rate)
blend_minus_popularity = accuracy - time_aware_popularity_accuracy
```

On the reference dataset (primary, 5 full-outcome-window months): blend 57.98% vs time-aware popularity 55.66% (+2.31pp) — see `docs/GLOBAL_TWO_MONTH_BLEND_IMPLEMENTATION_REQUIREMENTS-refined.md` for the full reproduction table and its caveats (exploratory, not a claim of proven superiority; three of the five primary months run on the bootstrap policy, where the blend IS the popularity arm and the two tie exactly).

**Determinism note:** `PolicyEngine.top_practices()`'s final ranking is tie-broken deterministically by practice name, and `_preference_key()`'s monthly-policy-selection tie-break is a strict total order — both are reproducible across runs regardless of hash seed.

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `BacktestEngine.__init__()` | `src/validation/backtest.py` | `APIService`, CLI | `recommender_engine, processor` → also stores `self.policy_engine = recommender_engine.policy_engine` |
| `BacktestEngine.run_backtest()` | `src/validation/backtest.py` | `APIService.run_backtest()`, CLI `_validate_recommendations()` | `cancellation_check: Callable \| None` → `{status, per_month_results, primary, sensitivity, cancelled}` — no config dict, no `train_ratio` |
| `BacktestEngine.cancel()` / `reset_cancellation()` | `src/validation/backtest.py` | `APIService.cancel_backtest()`; internally at the top of `run_backtest()` | moved here from the deleted `OptimizationEngine` |
| `BacktestEngine._score_month()` | `src/validation/backtest.py` | `run_backtest()` | one prediction month → `(row, improvements_per_case, expected_mrr_per_case, was_cancelled)` |
| `BacktestEngine._aggregate_scope()` | `src/validation/backtest.py` | `run_backtest()` (primary and sensitivity, and any cancelled/empty scope) | replaces the old duplicated `_build_partial_results()` — one aggregation function used for every scope, complete or partial |
| `BacktestEngine._expected_random_mrr()` | `src/validation/backtest.py` | `_score_month()` (per case) | staticmethod; `n, k, top_n` → exact expected MRR under random selection |
| `BacktestEngine._baseline_from_k_avg()` | `src/validation/backtest.py` | `_aggregate_scope()` | staticmethod; `k_avg, total_practices, top_n` → P(≥1 correct by chance) |

## Cross-references
- **Related Use Case Skills:** `/uc-02-run-backtest-validation`
- **Related Domain Skills:** `/domain-ml` (`PolicyEngine` owns the cohort, selection, and scoring that `BacktestEngine` replays), `/domain-api` (routes expose the backtest + cancel endpoints)
