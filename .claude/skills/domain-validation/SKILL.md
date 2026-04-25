---
name: domain-validation
description: Rolling window backtest, grid search parameter optimization, accuracy metrics, cancellation. Use when modifying backtest logic, optimization search space, random baseline formula, or the cancel mechanism.
---

# Domain: Validation

## Summary
`BacktestEngine` validates recommendation accuracy using a rolling window approach; `OptimizationEngine` automates running many backtests to find the best parameter combination. Results are saved to `results/` as JSON.

## Data Flows

- **Backtest:** `BacktestEngine.run_backtest()` → iterates test months starting at index 3 → for each test month: calls `learn_sequences_up_to_month(test_month)`, then loops all teams → calls `recommender.recommend(team, prev_month, ...)` → checks improvements in `test_month`, `test_month+1`, `test_month+2` → accumulates accuracy per month → returns overall accuracy + random baseline
- **Optimization:** `OptimizationEngine.find_optimal_config()` → `generate_parameter_combinations()` yields dicts → for each: runs `run_backtest(config=combo)` → tracks best result → checks `_cancelled` flag every 10 teams and every month boundary → saves all results to `results/optimization_results_{timestamp}.json`
- **Cancellation:** `POST /api/optimize/cancel` → `APIService.cancel_optimization()` → `optimizer_engine.cancel()` → sets `_cancelled = True` → polled inside backtest loop → returns partial results dict with `cancelled: True`
- **Results persistence:** `OptimizationEngine.load_latest_results()` reads the most recent JSON file from `results/`; served by `GET /api/optimize/latest`

## Domain Validation Rules and Business Logic

- Rolling window starts at month index 3 (0-based); months 0–2 used only as training data
- Improvement validation window: checks `test_month`, `test_month+1`, `test_month+2` (3-month window to account for adoption lag)
- Teams with zero improvements in the 3-month window are excluded from accuracy calculation (not a model failure)
- `cancellation_check` callable is passed from `OptimizationEngine` into `BacktestEngine` and polled every 10 teams and at each month start

## Formulas / Scoring / Calculation Logic

**Overall accuracy:**
```
overall_accuracy = mean(per_month_accuracy for each test month)
```

**Random baseline** (probability of ≥1 correct recommendation by chance):
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

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `BacktestEngine.run_backtest()` | `src/validation/backtest.py:27` | `APIService.run_backtest()`, `OptimizationEngine` | `config: dict, cancellation_check: Callable` → results dict with `overall_accuracy`, `random_baseline`, `per_month_results`, `cancelled` |
| `BacktestEngine._build_partial_results()` | `src/validation/backtest.py:354` | `run_backtest()` on cancellation | internal; builds same structure as full results with `cancelled: True` |
| `OptimizationEngine.find_optimal_config()` | `src/validation/optimizer.py` | `APIService.find_optimal_config()` | param range lists, `min_accuracy`, `fixed_params` → results dict with `optimal_config`, `all_results`, `cancelled` |
| `OptimizationEngine.generate_parameter_combinations()` | `src/validation/optimizer.py:31` | `find_optimal_config()` | range lists → generator of config dicts |
| `OptimizationEngine.cancel()` | `src/validation/optimizer.py` | `APIService.cancel_optimization()` | sets `self._cancelled = True` |
| `OptimizationEngine.load_latest_results()` | `src/validation/optimizer.py` | `GET /api/optimize/latest` route | static method; reads most recent JSON from `results/` |

## Cross-references
- **Related Use Case Skills:** `/uc-02-run-backtest-validation`, `/uc-03-run-parameter-optimization`
- **Related Domain Skills:** `/domain-ml` (BacktestEngine wraps RecommendationEngine), `/domain-api` (routes expose backtest + optimize endpoints)
