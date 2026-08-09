# Finding 5: The random-baseline formula misuses a combinatorics function, and isn't independently verified

## Problem statement (user perspective)

The system calculates a "random baseline" number — an estimate of how well pure random guessing would do — using a probability formula built on combinatorics (counting how many ways you could pick a subset of items). That calculation depends on a math-library function (`scipy.special.comb`) that, in the exact mode used here, is designed to work with whole numbers (e.g., "30 practices, choose 2").

The code feeds that function a decimal average instead of a whole number, since the input (`k_avg`, the average number of practices improved per case) is averaged across many cases and usually isn't a clean integer. This creates two separate, independent problems:

1. **It works today, but it's living on borrowed time.** SciPy has already marked this exact usage (`exact=True` with non-integer inputs) as deprecated, with a warning that it will raise an error in a future SciPy release. The project's `requirements.txt` pins `scipy>=1.9.0` with no upper bound, so a routine `pip install --upgrade` at some point in the future could suddenly make the backtest and optimization features crash with no advance warning — the code only catches `ValueError`/`ZeroDivisionError` today, and there's no guarantee that's the exception type a future SciPy version will raise.
2. **Nobody has independently verified the formula is mathematically correct.** There's no test that takes a small, hand-checkable example (e.g., "3 practices total, 1 typically improves, guess 1 at random — what's the chance of being right?") and confirms the code's formula matches what you'd get by working it out by hand. The existing tests only check that the resulting number looks *plausible* (falls between 0 and 1, roughly tracks other related numbers) — not that it's actually correct.

Neither issue changes the current 50.3% / 2.14x figures on record today — this is a fragility and rigor concern (will it keep working, and is it provably right), not a "the current answer is wrong" concern.

*Note (2026-08-09): the headline figures moved from 24.4%/2.06x to 23.5%/2.14x as part of resolving [Finding 4](04-accuracy-vs-baseline-aggregation-mismatch.md) (aggregation-method fix, unrelated to the float/comb issue described here). That same fix also consolidated the previously-duplicated comb formula (was in both `run_backtest()` and `_build_partial_results()`) into a single static helper, `BacktestEngine._baseline_from_k_avg()` — so the fix below now only needs to be applied in one place instead of two.*

## Technical detail

- **File**: `src/validation/backtest.py`
- `BacktestEngine._baseline_from_k_avg()` (line ~62), the single place the comb formula now lives:
  ```python
  p_none = comb(total_practices - k_avg, top_n, exact=True) / comb(total_practices, top_n, exact=True)
  ```
  (line ~83) — `k_avg` (a float average, not an integer) is passed as part of `total_practices - k_avg` into `comb(..., exact=True)`. SciPy currently accepts this with a `DeprecationWarning`, and has announced it will raise an error for non-integer `N`/`k` with `exact=True` in a future release (SciPy 1.16 per the deprecation notice).
- Callers compute `k_avg = sum(cases) / len(cases)` (a float average) before calling the helper — both the per-month `k_avg` values (`run_backtest()`, ~line 460) and the pooled fallback (`run_backtest()` ~line 455, `_build_partial_results()` ~line 613) feed floats into it the same way.
- The surrounding `try/except (ValueError, ZeroDivisionError)` inside the helper provides a fallback approximation if the calculation fails today — but there's no guarantee the exception type SciPy raises once this becomes a hard error will be one of those two types, so the fallback isn't guaranteed to trigger correctly if/when this breaks.
- `tests/test_backtest.py` only asserts self-consistency of the resulting `random_baseline` value (e.g., it's within `[0, 1]`, and `improvement_gap` equals `accuracy - random_baseline` within a tolerance) — no test independently recomputes the hypergeometric probability for a known small `n`/`k`/`top_n` and checks the code's output against it.

## Suggested fix

Two independent fixes, one per issue:

1. **Stop passing a float into `exact=True`.** Either round `k_avg` to the nearest integer before calling `comb`, or switch to `comb(..., exact=False)` (which uses a continuous approximation and accepts floats natively — this is closer to what's actually being computed conceptually, since `k_avg` is already an average, not a count).
2. **Add an independent correctness test.** Write a small test with a hand-computable example — e.g. `n=3, k=1, top_n=1` → `P(at least one hit) = 1/3` — and assert the code's formula produces that exact value, separate from the existing self-consistency checks.

## Follow-on work after the code fix

1. Re-run the backtest after switching away from `exact=True` with a float — confirm the resulting `random_baseline` value is unchanged (or negligibly different) from the current 23.5%, since this is a mechanical fix, not a formula change.
2. Consider pinning an upper bound on `scipy` in `requirements.txt` (or at least noting the deprecation in a comment) so a future dependency upgrade doesn't silently introduce a new failure mode.

## Verification / done criteria

- `comb(...)` is called without triggering the `exact=True`-with-non-integer` deprecation warning.
- A new test independently verifies the random-baseline formula against a hand-computed example.
- The 23.5% random-baseline figure is confirmed unchanged (within rounding) after the fix.
- Someone can point at the fixed line and explain, in one sentence, what was fragile about the old code and why the fix removes that fragility.

---

## Resolution (2026-08-09)

**Decision:** `comb(..., exact=False)`, not rounding `k_avg`. Rationale: `exact=False` uses the
Gamma-function generalization of the binomial coefficient, which is the standard continuous
extension of "N choose k" to real-valued arguments — it accepts `k_avg`'s full precision natively
instead of discretizing it, and doesn't require picking an arbitrary rounding rule (nearest? up?
down?) that would make the result discontinuous as `k_avg` drifts across a `.5` boundary.

**Implementation** (`src/validation/backtest.py`, `BacktestEngine._baseline_from_k_avg()`, line
83): changed both `comb(...)` calls from `exact=True` to `exact=False`. No other logic in the
method changed — same guard conditions, same fallback approximation, same
`try/except (ValueError, ZeroDivisionError)`. The other two `comb(..., exact=True)` calls in this
file (`_expected_random_mrr()`, lines 51/56) were left untouched since they receive genuine
per-case integers, not an average — no deprecation risk applies there.

**Tests added** (`tests/test_backtest.py`):
- `test_baseline_from_k_avg_matches_hand_computed_value` — calls `_baseline_from_k_avg()` directly
  with the doc's hand-computable example (`n=3, k_avg=1, top_n=1` → `1/3`), independent of the
  existing self-consistency checks.
- `test_baseline_from_k_avg_handles_fractional_k_avg` — a genuinely fractional case (`n=5,
  k_avg=1.5, top_n=1` → `0.3`), run with `DeprecationWarning` elevated to an error, confirming the
  fixed call path raises nothing.

**Verified:**
- `BacktestEngine._baseline_from_k_avg(1, 3, 1)` returns `0.3333...` with `warnings.simplefilter('error')` active — no `DeprecationWarning`.
- `make test-file FILE=test_backtest.py` and `test_temporal_boundaries.py` pass.
- Re-ran the real `BacktestEngine.run_backtest()` against `data/raw/combined_dataset.xlsx`
  (defaults): **50.3% accuracy vs. 23.5% random baseline = 2.14x** — unchanged from the
  post-Finding-4 figures, confirming this was a mechanical fix, not a formula change.

**One sentence:** the old code fed a float average into a SciPy function whose exact-integer mode
was about to start raising errors on non-integers; switching to the function's native
continuous-value mode removes that fragility without changing the computed result.

**Out of scope, left open:** the deeper Jensen's-inequality nuance also raised in
[Finding 4](04-accuracy-vs-baseline-aggregation-mismatch.md) — `_baseline_from_k_avg()` computes
`P_none(avg k)` rather than `avg(P_none(k))` per case (as `_expected_random_mrr()` already does
correctly for MRR). Because the no-hit probability is convex in `k`, these aren't equal in
general; not addressed here per explicit scope decision.
