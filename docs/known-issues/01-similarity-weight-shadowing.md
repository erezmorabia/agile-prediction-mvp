# Finding 1: The similarity/sequence "blend knob" doesn't actually work

## Problem statement (user perspective)

The recommendation engine is supposed to build each suggestion by mixing two signals:

- **"What did similar teams do next"** (collaborative filtering)
- **"What usually follows this kind of improvement"** (sequence learning)

These two signals are meant to be combined using a fixed, tunable ratio — by default 60% weight on the similar-teams signal, 40% on the sequence signal. This ratio is exposed as a parameter (`similarity_weight`) and is even one of the dimensions the parameter-optimization grid search tries different values for, in search of the best-performing configuration.

In practice, that ratio is never actually used. It gets silently overwritten every single time a recommendation is generated, replaced by a number that has nothing to do with the intended blend — instead it becomes whatever the last "similar team" in that call's list happened to score for similarity. That number is data-dependent: it changes from team to team and month to month, and it's always fairly high (≥ 0.75, since teams below that threshold aren't included as "similar" at all).

Consequences:
- The 60/40 blend described in the documentation and shown to users has never actually run as documented.
- The optimizer has been grid-searching this parameter as if it mattered, but every value it tries gets thrown away before it's used — so any "optimal `similarity_weight`" reported by past optimization runs is meaningless.
- The real, live accuracy numbers currently on record (headline: 50.3% accuracy, 2.06x better than random) were produced under this bug, not under the documented algorithm — they need to be regenerated after the fix.

## Technical detail

- **File**: `src/ml/recommender.py`, function `RecommendationEngine.recommend()`
- **Root cause — variable shadowing**: at line 158, the loop
  ```python
  for similar_team, similarity_weight, historical_month in similar_teams:
  ```
  unpacks each similar team's **cosine-similarity score** into a variable named `similarity_weight` — which is also the name of the function's own parameter (default `0.6`, line 32) representing the blend ratio.
- This loop always runs to completion (no early break that would leave the pre-loop value intact), so by the time the code reaches the actual blend formula at line 272:
  ```python
  practices_scores[practice] = similarity_weight * sim_score + (1.0 - similarity_weight) * seq_score
  ```
  `similarity_weight` no longer holds the caller's intended constant (e.g. `0.6`) — it holds the similarity score of the *last* team in `similar_teams` (which, since the list is sorted descending and filtered by `min_similarity_threshold`, defaults to 0.75, is always ≥ 0.75).
- Line 158's usage of that same loop variable at line 207 (`similarity_scores[practice_name] += similarity_weight * improvement_magnitude`) is **correct** and matches the intended per-team weighting — the bug is isolated to the leak into the Step-4 combine formula at line 272.

## Suggested fix

Rename the loop variable so it stops colliding with the function parameter:

```python
for similar_team, peer_similarity, historical_month in similar_teams:
    ...
    similarity_scores[practice_name] += peer_similarity * improvement_magnitude
```

Leave line 272 (`similarity_weight * sim_score + (1.0 - similarity_weight) * seq_score`) untouched — once the shadowing is gone, it will correctly reference the function's real parameter again.

## Follow-on work after the code fix

1. Run `make test-file FILE=test_temporal_boundaries.py` (required after any `src/ml/` change per this project's `CLAUDE.md`) to confirm no data-leakage regression.
2. Re-run the backtest / parameter optimization to get corrected accuracy and random-baseline numbers — expect these to differ from the current 50.3% / 2.06x figures.
3. Update every place that cites the old "50.3% accuracy — 2.06x better than random" figure:
   - `.claude/rules/product.md` (Domain Story line)
   - `docs/PROJECT_DOCUMENTATION.md` (results/optimization sections)
   - anywhere else `grep -r "50.3\|2.06" --include=*.md` finds a hit
4. Check `.claude/skills/domain-ml/SKILL.md` for a description of the blend formula that may need updating to match the corrected behavior.

## Verification / done criteria

- Temporal-boundary tests pass.
- A fresh backtest/optimizer run produces a new, internally-consistent accuracy figure.
- All docs referencing the old headline numbers are updated to the new ones.
- Someone can point at the fixed line and explain, in one sentence, what was wrong and why the fix is correct.

## Resolution (2026-08-09)

Fixed by renaming the shadowing loop variable in `RecommendationEngine.recommend()`
(`src/ml/recommender.py`, was line 158/207) to `peer_similarity`, per the suggested fix above.
`test_temporal_boundaries.py` and the full `src/ml`/API test suite pass.

Re-ran the parameter-optimization grid search (180 combinations, same default ranges) against
the corrected code. Result: `optimal_config` is identical to the previous default except
`similarity_weight` is now `0.7` instead of `0.6` — every other parameter (`top_n=2`,
`k_similar=19`, `similar_teams_lookahead_months=3`, `recent_improvements_months=3`,
`min_similarity_threshold=0.75`) is unchanged. Because the bug made `similarity_weight`
inert, the *old* "50.3%/2.06x" figures were, by coincidence, already generated with an
effective weight that behaved like ~0.75+ (the leaked value was always ≥ `min_similarity_threshold`)
— close enough to the new true optimum of 0.7 that headline numbers barely moved:

| Metric | Old (buggy) | New (fixed, re-optimized) |
|---|---|---|
| Accuracy | 50.3% | 50.3% (50.29%) |
| Random baseline | 24.4% | 24.4% |
| Improvement factor | 2.06x | 2.06x (2.058x) |
| Popularity baseline | 43.6% | 43.6% (unaffected — no dependency on `similarity_weight`) |
| MRR improvement factor | 2.21x | 2.23x (only metric with a real, non-rounding change) |

**Default-parameter decision:** checked the per-month backtest breakdown for `similarity_weight`
0.6 vs 0.7 — 6 of 7 test months are identical between the two, and 0.7 strictly wins the 7th
(38.5% vs 30.8%); 0.7 also beats 0.6 on precision@N, recall@N, and MRR. Since no additional
validation data is expected, 0.7 weakly dominates 0.6 on all available evidence with no
tradeoff identified. Decision: updated `RecommendationEngine.recommend()`'s `similarity_weight`
default from `0.6` to `0.7` in code (`src/ml/recommender.py`), plus every place that echoed that
default: `src/api/models.py` (`BacktestConfig`), `src/api/service.py`, `src/validation/backtest.py`
(fallback + docstring), and the docs/examples listed below.

Docs updated: `docs/PROJECT_DOCUMENTATION.md` §3.5, §6.5 (default now `0.7`, explains the bug and
why 0.7 was chosen), the two worked examples in §4 (recomputed combined/final scores at 0.7 —
rankings unchanged), the MRR improvement-factor cells in §3.6/§6.3, and the JSON/Python code
samples that echoed `0.6`; `README.md`'s two "Configuration" bullets; `.claude/skills/domain-ml/SKILL.md`.
No other doc needed a numeric change — `.claude/rules/product.md`'s "50.3%/2.06x" line and
`.claude/skills/domain-validation/SKILL.md`'s "~50.3%/~24.4%" line remained accurate at their
reported precision and were left as-is.

**Separately tracked:** `similar_teams_lookahead_months` has the same class of bug (dead
parameter, hardcoded `max_months_ahead = 3` in the function body) — noted for a future fix,
out of scope here.

**Also discovered and fixed (2026-08-09):** `web/static/js/app.js`'s "Find Optimal Config" flow
hardcoded `similarity_weight` to `0.6` as a `fixed_params` entry (excluded from the search grid
entirely) with UI copy explicitly labeling it "Fixed Parameters (Non-Impactful): Analysis showed
0.6-0.8 produce identical results" — a direct downstream artifact of this same bug (that
"analysis" was run against the buggy code, where it was true only because the parameter was
inert).

Fix: removed the `fixed_params` override and changed `similarity_weight_range` from `[0.6]` to
`[0.6, 0.7, 0.8]` (same grid the backend's own default range uses). To avoid tripling the search
space (324 → 972 combinations, an unreasonable ~65 min for a synchronous browser action),
`min_similarity_threshold_range` was trimmed from 3 values to 2 (`[0, 0.5, 0.75]` →
`[0.5, 0.75]`) — `0` was dropped because it never won in the backend's own default-grid run and
tied exactly with `0.5` every time it was tested, so it carried no additional information. Net
search space: 4 × 3 × 3 × 2 × 3 × 3 = 648 combinations (~43 min), still fully searching the
parameter that was previously fixed. Updated the results-rendering copy to drop the "Fixed
Parameters (Non-Impactful)" section and list Similarity Weight under "Optimized Ranges Tested"
instead. Verified end-to-end with Playwright (confirmed the rendered "Parameter Ranges Tested"
panel and search-space text) and via a direct `/api/optimize` call showing accuracy genuinely
varies with `similarity_weight` (0.6 → 49.2%, 0.7 → 49.7%) when passed as a real range instead
of `fixed_params`.

**Also discovered and fixed (2026-08-09):** the manual "Run Backtest" flow's Similarity Weight
slider still defaulted to `0.6` on page load — `web/index.html`'s slider `value` and display
spans, and the `|| 0.6` fallback in `getBacktestConfig()` (`web/static/js/app.js`) — both stale
relative to the `0.7` default now used everywhere else. Since the slider always sends an
explicit value (never "unset"), a fresh page load + "Run Backtest" with no slider interaction
silently sent `0.6` on the wire, overriding the corrected server-side default. Note: "Run
Backtest" is *never* automatically based on the optimizer's result either way — it always reads
whatever the sliders currently show at click time; the only link between the two flows is the
manual "Apply This Configuration" button after a Find Optimal Config run, which copies the
optimal values into these same sliders. Fixed the slider default and JS fallback to `0.7`;
verified via Playwright that a fresh page load's "Run Backtest" now sends `similarity_weight: 0.7`.

**Full sweep for remaining `0.6` references (2026-08-09):** grepped the entire repo for `0.6`
after the above fixes and found two more stale, user-facing "the default is 0.6/0.4" claims that
had been missed: the "How the recommendation works" explanation panel rendered in the live
Recommendations tab (`web/static/js/app.js`, the `displayRecommendations()` formula/note text)
and the formula walkthrough in `README.md`'s "How It Works" section. Both updated to `0.7`/`0.3`.
Everything else matching `0.6` in the repo was checked and is unrelated or still correct as-is:
`train_ratio=0.6` in `examples/demo.py` and `scripts/*.py` is a different, already-deprecated
parameter (the rolling-window backtest ignores it entirely — see `run_backtest()`'s docstring);
`similarity_weight_range: [0.6, 0.7, 0.8]` in `optimizer.py`/`cli.py`/`app.js` is the intentional
grid still searched around the new default; values in `tests/test_optimizer.py` are arbitrary
test fixtures for the grid-generation mechanism, not defaults; and `0.6`/`0.67` appearing as
maturity-level or probability values elsewhere (e.g. `0.67` = Level 2 normalized) are unrelated
numbers that happen to match.
