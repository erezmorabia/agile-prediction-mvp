# Finding 4: The headline "accuracy" and "random baseline" numbers are computed with different averaging methods

## Problem statement (user perspective)

The system reports a single "accuracy" percentage (currently 50.3%) and compares it against a "random baseline" — an estimate of how well pure guessing would do (currently 24.4%) — to produce the headline claim "2.06x better than random."

Those two numbers are built with different recipes:

- **Accuracy** is calculated separately for each month, then those monthly figures are averaged together (a "macro-average" — every month counts equally, regardless of how many predictions happened that month).
- **Random baseline** is calculated once, using a single average pooled across *every* prediction from *every* month combined (a "micro"-style average — every individual prediction counts equally, months don't matter).

Dividing "accuracy" by "random baseline" to get 2.06x therefore divides two numbers that weren't built the same way. This isn't necessarily wrong, but it's not a clean apples-to-apples comparison either, and nothing in the documentation or code comments calls this out — a reader would reasonably assume both halves were computed identically.

**This is a design decision waiting to be made, not a one-line bug fix.** Once flagged, someone has to decide: should the random baseline also be computed per-month and averaged the same way as accuracy, to make the comparison consistent? Or is the current mixed approach an acceptable simplification worth documenting explicitly instead of changing?

## Technical detail

- **File**: `src/validation/backtest.py`
- **Accuracy** (line 392): macro-average of per-month rates —
  ```python
  overall_accuracy = sum(r["accuracy"] for r in per_month_results) / len(per_month_results)
  ```
- **Random baseline** (line 419): a single `k_avg` computed once, pooled across every case in every month —
  ```python
  k_avg = sum(improvements_per_case) / len(improvements_per_case)
  ```
  (`improvements_per_case` is accumulated across the entire backtest run, not reset or averaged per month) — this `k_avg` then feeds directly into the random-baseline formula, producing one baseline figure for the whole run, not a per-month figure that gets averaged the same way `overall_accuracy` is.
- **The comparison** (`improvement_gap = overall_accuracy - random_baseline`, and the "2.06x" ratio derived from it elsewhere) divides/subtracts these two differently-aggregated quantities directly.

## Suggested direction (not a prescribed fix — needs a decision)

Two reasonable options, either of which resolves the inconsistency — this doc doesn't pick one, since it changes the headline number and should be a deliberate choice:

1. **Make the baseline match accuracy's aggregation**: compute a per-month random baseline (using that month's own `k_avg` across only that month's cases) and macro-average those, the same way `overall_accuracy` is computed.
2. **Make accuracy match the baseline's aggregation**: report a single pooled `total_correct / total_predictions` figure instead of a macro-average, and compare that against the existing pooled baseline.

Either way, the two numbers being divided against each other should be built the same way.

## Follow-on work after a decision is made

1. Whichever direction is chosen, re-run the backtest to get the corrected, consistently-aggregated figures.
2. Update every place citing the current "50.3% / 24.4% / 2.06x" figures (same list as Finding 1: `.claude/rules/product.md`, `docs/PROJECT_DOCUMENTATION.md`, anywhere `grep -r "50.3\|2.06\|24.4"` finds).
3. Consider adding a short code comment at the random-baseline calculation explicitly stating which aggregation method was chosen and why, so this doesn't need re-discovering later.

## Verification / done criteria

- `overall_accuracy` and `random_baseline` are computed using the same aggregation method (both macro-averaged per month, or both pooled).
- The updated headline figures are reflected consistently across all docs.
- Someone can explain, in one sentence, which aggregation method was chosen and why.

---

## Appendix — a secondary, lower-confidence nuance (worth knowing, not worth fixing)

There's a second, subtler property of the random-baseline formula itself, separate from the aggregation-method mismatch above. It was surfaced by one pass of code exploration and has **not** been independently re-verified line-by-line with the same rigor as the finding above — treat it as a "good to know if asked" point, not a confirmed defect:

The random-baseline formula ("probability of at least one correct pick out of N random guesses") is a curved (concave) function of `k` — the average number of things that actually improved. Plugging in the *average* `k` (`k_avg`) and computing the probability once, versus computing the probability separately for each case's *own* `k` and then averaging those probabilities, can give slightly different answers whenever the formula is nonlinear in `k` — the code's own docstring for a related metric (MRR) explicitly acknowledges this distinction and computes it the "per-case" way for that metric, but the headline random baseline does it the simpler "average first" way instead.

**If this holds up under closer scrutiny**, the practical implication is reassuring rather than alarming: because the curve bends the way it does, the "average-first" shortcut used here would tend to slightly *overstate* the random baseline compared to the more rigorous per-case method — meaning the true "improvement over random" would be **at least as good as**, not worse than, the reported 2.06x. In other words, if there's an error here, it likely makes the current headline claim conservative, not inflated.

Not recommended as something to act on now — flagging it here so it's on record and can be revisited if someone wants to make the random-baseline math fully rigorous later.
