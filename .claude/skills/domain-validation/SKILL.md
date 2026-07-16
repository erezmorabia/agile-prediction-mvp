---
name: domain-validation
description: Rolling window backtest, grid search parameter optimization, accuracy metrics, cancellation. Use when modifying backtest logic, optimization search space, random baseline formula, or the cancel mechanism.
---

# Domain: Validation

## Summary
`BacktestEngine` validates recommendation accuracy using a rolling window approach; `OptimizationEngine` automates running many backtests to find the best parameter combination. Results are saved to `results/` as JSON.

## Data Flows

- **Backtest:** `BacktestEngine.run_backtest()` → iterates test months starting at index 3 → for each test month: calls `learn_sequences_up_to_month(test_month)`, then loops all teams → calls `recommender.recommend(team, prev_month, ...)` → checks improvements in `test_month`, `test_month+1`, `test_month+2` → accumulates accuracy, precision@N, recall@N, and MRR per month → returns overall values + matching random baselines for each
- **Optimization:** `OptimizationEngine.find_optimal_config()` → `generate_parameter_combinations()` yields dicts → for each: runs `run_backtest(config=combo)` → tracks best result → checks `_cancelled` flag every 10 teams and every month boundary → saves all results to `results/optimization_results_{timestamp}.json`
- **Cancellation:** `POST /api/optimize/cancel` → `APIService.cancel_optimization()` → `optimizer_engine.cancel()` → sets `_cancelled = True` → polled inside backtest loop → returns partial results dict with `cancelled: True`
- **Results persistence:** `OptimizationEngine.load_latest_results()` reads the most recent JSON file from `results/`; served by `GET /api/optimize/latest`

## Domain Validation Rules and Business Logic

- Rolling window starts at month index 3 (0-based); months 0–2 used only as training data
- Improvement validation window: checks `test_month`, `test_month+1`, `test_month+2` (3-month window to account for adoption lag)
- Teams with zero improvements in the 3-month window are excluded from accuracy calculation (not a model failure)
- `cancellation_check` callable is passed from `OptimizationEngine` into `BacktestEngine` and polled every 10 teams and at each month start

## Formulas / Scoring / Calculation Logic

**Overall accuracy (HR@N, i.e. Hit Rate@N / Success@N):** binary per case — 1 if *any* recommended
practice is in `actual_improved`, else 0.
```
overall_accuracy = mean(per_month_accuracy for each test month)
```

**Random baseline for HR@N** (probability of ≥1 correct recommendation by chance):
```
random_baseline = 1 − C(n − k_avg, top_n) / C(n, top_n)
```
- `n` = total number of practices
- `k_avg` = average number of improvements per team/month case
- `top_n` = number of recommendations generated
- Falls back to `min(1.0, (k_avg / n) * top_n)` if combination calculation fails

**Improvement factor:**
```
improvement_factor = overall_accuracy / random_baseline
```

### Supplementary rank-aware metrics (precision@N, recall@N, MRR)

HR@N is a standard top-N recommender metric, but it discards rank (an ordered list is
collapsed to a set before checking for a hit) and gives full credit even when only one of
`top_n` recommendations was right. `MetricsCalculator` (`src/validation/metrics.py`) already
implements the per-case pieces — `calculate_hit_rate` (precision@N) and `calculate_mrr` — and
`BacktestEngine.run_backtest()` wires them in per case, alongside a per-case recall@N calc,
aggregated the same way as accuracy (per-month mean → overall mean):

```
precision@N (case) = hits / top_n                       # MetricsCalculator.calculate_hit_rate
recall@N (case)    = hits / |actual_improved|            # hits / k for that case
mrr (case)         = 1 / rank of first hit, else 0        # MetricsCalculator.calculate_mrr
```

**Random baselines** — these are *not* the same formula as HR@N's baseline; each metric needs
its own chance-level comparison:

```
random_precision = k_avg / n     # exact — E[hits]/N is linear in k, so k_avg is safe to use
random_recall    = top_n / n     # exact — doesn't depend on k at all
random_mrr       = mean(expected_mrr_per_case)   # NOT derived from k_avg — nonlinear in k
```

`random_mrr` is computed per case (`BacktestEngine._expected_random_mrr(n, k, top_n)`) via the
negative hypergeometric rank distribution — `P(first hit at rank r) = C(n-r, k-1) / C(n, k)` —
then averaged, because averaging the *inputs* (k) first and computing MRR from `k_avg` would
give a different (wrong) answer than averaging the *outputs*.

**Two caveats when reading these numbers:**
- Recall@N is capped at `top_n / |actual_improved|` by construction — a team that improved 5
  practices can never exceed recall 0.4 at the default `top_n=2`. A low recall reflects the cap,
  not necessarily a weaker model.
- Precision@N equals HR@N only when `top_n=1`. At the default `top_n=2`, 1-of-2 correct scores
  HR@N=1.0 but precision@N=0.5 — this gap is exactly the leniency HR@N has relative to precision.

Each has a matching gap/factor field (e.g. `precision_gap`, `precision_improvement_factor`),
mirroring `improvement_gap`/`improvement_factor` for HR@N.

### Popularity baseline (supplementary, alongside random)

A stronger sanity check than random chance: always recommend the top-N practices that improve
most often organization-wide (ignoring the target team's own state entirely), learned from the
same months < `prev_month` cutoff the real model just used for that case. Computed inline in the
per-team loop right after the real recommendation's hit check, reusing
`sequence_mapper.get_improvement_frequency()` (already populated as a side effect of the
`recommend()` call that just ran — no extra learning pass needed):

```
popularity_recommended = top_n practices by improvement_freq, excluding this team's maxed-out practices
popularity_accuracy = mean(per_month popularity hit-rate)   # same per-month-mean aggregation as HR@N
popularity_gap = overall_accuracy - overall_popularity_baseline
popularity_improvement_factor = overall_accuracy / overall_popularity_baseline
```

On the reference dataset this comes out to ~43.6% (vs. the model's ~50.3%, and random's ~24.4%)
— most of the model's edge over random is attributable to organization-wide popularity alone;
the smaller remaining margin (~1.15x) over the popularity baseline is what's actually
attributable to per-team personalization (collaborative filtering + sequences).

**Determinism note:** `RecommendationEngine.recommend()`'s final ranking is tie-broken
deterministically by practice name (see `/domain-ml`) — without that fix, tied scores at the
top-N cutoff resolved via Python's hash-seed-dependent set iteration order, making backtest
accuracy non-reproducible across process runs.

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `BacktestEngine.run_backtest()` | `src/validation/backtest.py:62` | `APIService.run_backtest()`, `OptimizationEngine` | `config: dict, cancellation_check: Callable` → results dict with `overall_accuracy`, `random_baseline`, `overall_popularity_baseline` (+ `popularity_gap`/`popularity_improvement_factor`), `overall_precision`/`overall_recall`/`overall_mrr` (+ matching random baselines), `per_month_results`, `cancelled` |
| `BacktestEngine._expected_random_mrr()` | `src/validation/backtest.py:30` | `run_backtest()` (per case) | staticmethod; `n, k, top_n` → exact expected MRR under random selection, via negative hypergeometric rank distribution |
| `BacktestEngine._build_partial_results()` | `src/validation/backtest.py:496` | `run_backtest()` on cancellation | internal; builds same structure as full results with `cancelled: True` |
| `OptimizationEngine.find_optimal_config()` | `src/validation/optimizer.py` | `APIService.find_optimal_config()` | param range lists, `min_accuracy`, `fixed_params` → results dict with `optimal_config`, `all_results`, `cancelled` |
| `OptimizationEngine.generate_parameter_combinations()` | `src/validation/optimizer.py:31` | `find_optimal_config()` | range lists → generator of config dicts |
| `OptimizationEngine.cancel()` | `src/validation/optimizer.py` | `APIService.cancel_optimization()` | sets `self._cancelled = True` |
| `OptimizationEngine.load_latest_results()` | `src/validation/optimizer.py` | `GET /api/optimize/latest` route | static method; reads most recent JSON from `results/` |

## Cross-references
- **Related Use Case Skills:** `/uc-02-run-backtest-validation`, `/uc-03-run-parameter-optimization`
- **Related Domain Skills:** `/domain-ml` (BacktestEngine wraps RecommendationEngine), `/domain-api` (routes expose backtest + optimize endpoints)
