# Finding 2: The "how many months ahead to look" setting doesn't actually adjust anything

**Status: Resolved (2026-08-09).** `RecommendationEngine.recommend()` and
`get_recommendation_explanation()` both now read `similar_teams_lookahead_months` instead of a
hardcoded `3`. See `src/ml/recommender.py`. Bundled in the same pass: `get_recommendation_explanation()`
previously had its own hardcoded `max_months_ahead = 3` with no lookahead parameter at all — fixed by
adding a `similar_teams_lookahead_months` parameter (default `3`, matching `recommend()`) so the
explanation always describes the same window used to produce the score, the same parity `recommend()`
already has for `k_similar`/`min_similarity_threshold` after Finding 3.

## Problem statement (user perspective)

When the recommendation engine finds a team similar to yours, it looks at what that similar team improved in the months *after* the point they were considered similar, and uses that as one of its signals. How many months ahead to check is exposed as a configurable setting (`similar_teams_lookahead_months`), and — like the blend ratio in Finding 1 — it's one of the dimensions the parameter-optimization grid search tries different values for, looking for the best-performing configuration.

In practice, this setting is completely disconnected from the code that uses it. No matter what value is configured — 1, 2, 3, or anything else — the system always checks exactly 3 months ahead, because that number is hardcoded directly into the logic instead of reading the configurable value.

Consequences:
- Changing this setting in a request or during optimization has **zero effect** on the recommendations produced.
- Any past optimization result that reports a particular value of `similar_teams_lookahead_months` as "optimal" is meaningless — every value in the grid produces identical behavior, because none of them were ever actually applied.
- This is the same *shape* of problem as Finding 1: a parameter that looks live, is documented, and is even searched over by the optimizer, but was never wired through to the code path that should read it.

## Technical detail

- **File**: `src/ml/recommender.py`, function `RecommendationEngine.recommend()`
- The function signature (line 33) declares:
  ```python
  similar_teams_lookahead_months: int = 3,
  ```
- But inside the function body (line 174), the lookahead window is hardcoded instead of reading that parameter:
  ```python
  max_months_ahead = 3
  ```
- `max_months_ahead` — not `similar_teams_lookahead_months` — is what's actually used in the loop that walks 1..N months ahead of a similar team's historical snapshot. The parameter is accepted, documented, and even grid-searched by `OptimizationEngine`, but it's never referenced anywhere in the function body.

## Suggested fix

Replace the hardcoded constant with the actual parameter:

```python
max_months_ahead = similar_teams_lookahead_months
```

Since the default value of the parameter (`3`) matches the current hardcoded constant, fixing this **will not change behavior when the default is used** — it only starts to matter once someone (or the optimizer) sets `similar_teams_lookahead_months` to something other than 3. This makes the fix low-risk to apply alongside Finding 1's fix in the same pass.

## Follow-on work after the code fix

1. Run `make test-file FILE=test_temporal_boundaries.py` (required after any `src/ml/` change per this project's `CLAUDE.md`) to confirm no data-leakage regression. **Correction:** the lookahead window is *not* the mechanism that prevents using future data — that's the independent `if similar_future_month > current_month: break` check in both `recommend()` and `get_recommendation_explanation()`, which fires regardless of how large `max_months_ahead` is. Widening the lookahead cannot cause leakage; the test is still worth running as a general regression check on any `src/ml/` change, not because this specific fix is riskier than it looks.
2. Re-run the parameter optimization grid search — now that `similar_teams_lookahead_months` actually affects the result, its search dimension may surface a genuinely different optimal value than `3`.
3. If the optimizer's reported "best config" changes as a result, re-check whether the headline accuracy figure needs updating again (on top of any change already made for Finding 1).

## Verification / done criteria

- Temporal-boundary tests pass (185 passed, 8 skipped — full suite, post-fix).
- Manually confirmed the parameter is now live: for team `AADS` at month `20200608`
  (`min_similarity_threshold=0.0` to guarantee a peer pool), `similar_teams_lookahead_months=1`
  ranks `Demo` first, `=3` ranks `Scrum Master` first, and `=6` changes the ranked set again —
  the same call previously returned identical results for every value of this parameter.
- Someone can point at the fixed lines (`src/ml/recommender.py:176` in `recommend()`,
  `:411` in `get_recommendation_explanation()`) and explain, in one sentence, what was wrong and
  why the fix is correct.
