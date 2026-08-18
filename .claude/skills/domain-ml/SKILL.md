---
name: domain-ml
description: ML engine - collaborative filtering (cosine similarity), empirical practice transitions, time-aware popularity, and the global two-month adaptive blend policy. Use when modifying recommendation logic, similarity search, sequence learning, popularity scoring, or monthly policy selection.
---

# Domain: ML

## Summary
Three evidence components produce practice recommendations. `SimilarityEngine` finds peers via cosine similarity. `SequenceMapper` learns empirical transitions between consecutive improvement-bearing steps and also tracks organization-wide practice-improvement counts (popularity). `PolicyEngine` (`src/ml/policy.py`) owns the global two-month adaptive blend: it selects one policy per prediction month from prior completed outcomes and scores similarity/sequence/time-aware-popularity evidence under it. `RecommendationEngine` is a thin compatibility wrapper that constructs and delegates to a `PolicyEngine`.

## Data Flows

- **Recommendation:** `RecommendationEngine.recommend(team, prediction_month)` → `PolicyEngine.recommend()` → `is_recommendable()` (baseline exists + ≥2 non-maxed candidates) → `select_policy(prediction_month)` (from completed prior months, or `BOOTSTRAP_POLICY` if none) → `score_case()` blends similarity/sequence/popularity under that policy → top 2 by `(-score, name)`
- **Case components:** `PolicyEngine.case_components(team, baseline_month)` (cached) computes, per (team, baseline): candidate practices, full ranked+deduped peer list (`k=num_teams, min_similarity=0.0`) with per-peer improvement contributions, the target's own sequence-trigger evidence, and org-wide historical/recent popularity counts for that baseline month
- **Policy variants without re-querying:** `SimilarityEngine.find_similar_teams` dedups by team name *before* truncating to `k`, so fetching once at `k=num_teams, min_similarity=0.0` and then filtering-by-threshold-then-truncating-to-`k` (`PolicyEngine._selected_peer_indices`) reproduces every `(peer_count, min_similarity)` variant in the 9-combination grid exactly
- **Explanation:** `RecommendationEngine.get_recommendation_explanation(team, prediction_month, practice)` → `PolicyEngine.explain_practice()` — re-derives the selected policy's peer subset and looks up whether each selected peer's cached contribution touched `practice`; returns a breakdown dict (`similar_teams_list`, `similar_teams_improved`, `has_sequence_boost`, `no_similar_teams_found`)
- **Sequence cache:** `learn_sequences_up_to_month(max_month)` stores results in `_sequence_cache[max_month]`; subsequent calls with the same max_month return from cache. `PolicyEngine._month_popularity(baseline_month)` calls this once per baseline month and also extracts `get_practice_popularity()` immediately into a plain dict, so later mutations of the shared mapper never affect an already-cached `CaseComponents`

## Domain Validation Rules and Business Logic

- Only data from months **< baseline_month** is used for sequence learning, popularity, and similarity matching (data leakage prevention)
- Similar teams deduplicated by team name — only the highest-similarity historical snapshot is kept per team
- Practices at normalized score ≥ 1.0 are excluded from the candidate set (already at max maturity)
- **Fixed component windows, never tunable:** `FIXED_LOOKAHEAD_SNAPSHOTS = 2` (similarity: peer's observed snapshots after it looked similar) and `FIXED_RECENCY_SNAPSHOTS = 2` (sequence: target team's own preceding observed snapshots); see `src/ml/policy.py`.
- **Baseline** for a (team, prediction_month) case = the team's own most recent observed snapshot strictly before `prediction_month` (`PolicyEngine.baseline_month_for`), not necessarily the prior *global* month — generalizes correctly if a team has data gaps (none exist in the current dataset, verified)
- **Recommendable** (no outcome required, used by the live flow): baseline exists AND ≥2 candidate practices. **Evaluable** (used by cohorts/backtest): recommendable AND at least one observed improvement in the 3-snapshot outcome window after baseline
- A missing/empty peer list is not an error: `PolicyEngine._compute_components` catches `ValueError` from `find_similar_teams` and sets `no_similar_teams_found=True`; similarity contributes 0 and the blend still returns 2 recommendations from sequence + popularity
- Sequence transitions are empirical cross-products between consecutive improvement-bearing steps; simultaneous improvements have no directed edge (see `SequenceMapper._learn_team_transitions()`)

## Formulas / Scoring / Calculation Logic

**Blend (per candidate practice):**
```
final_score = similarity_weight × similarity_norm + sequence_weight × sequence_norm + popularity_weight × popularity
popularity   = recency_weight × recent_popularity_norm + (1 - recency_weight) × historical_popularity_norm
```
- The three factor weights are one of 15 combinations of `(0, 0.25, 0.5, 0.75, 1.0)` summing to exactly 1.0 (`WEIGHT_TRIPLES`)
- `recency_weight` ∈ `(0.0, 0.25, 0.5, 0.75, 1.0)`, `peer_count` ∈ `(5, 10, 19)`, `min_similarity` ∈ `(0.0, 0.5, 0.75)` — full grid is `POLICY_GRID`, 675 combinations
- **Normalization scope differs by component:**
  | Component | Scope |
  |---|---|
  | Similarity | normalize over all evidence (may include maxed-out practices) → mask to candidates |
  | Sequence | normalize over all evidence → mask to candidates |
  | Historical popularity | mask to candidates → normalize |
  | Recent popularity | normalize org-wide → mask to candidates |
- Deterministic tie-break: final ranking sorts by `(-score, practice_name)`, exactly as before

**Similarity evidence (per peer, per practice):** `similarity_score × best_improvement_magnitude` where the magnitude is the max improvement across the fixed 2-snapshot look-ahead from the peer's historical month, gated to not exceed the target's baseline month

**Sequence evidence:** for each practice the target improved in its own preceding 2 snapshots (canonical `self.practices` order, not raw set iteration — same reproducibility fix as before), sum `get_typical_next_practices(practice, top_n=3)` transition probabilities into the successor practices

**Popularity evidence:** historical = org-wide improvement counts from `learn_sequences_up_to_month(baseline_month)` (strictly before baseline); recent = org-wide improvement counts for the single immediately-preceding observed transition into baseline (complementary windows, no overlap)

## Global Monthly Policy Selection

- `PolicyEngine.select_policy(prediction_month)`: if `completed_prior_months(prediction_month)` is empty, use `BOOTSTRAP_POLICY` (100% popularity, 50% recency); otherwise `max()` over the full 675-policy grid by `(mean_hit_rate_over_completed_months, *_preference_key(policy))`
- `_preference_key`: `(popularity_weight, -recency_weight, -similarity_weight, -sequence_weight, -peer_count_index, -threshold_index)` — a strict total order (ported from `scripts/research_full_per_team_optimization.py:prefer()`)
- `completed_prior_months(month)`: earlier prediction months whose own 3-snapshot outcome window has fully closed *before* `month`'s index — not the same as that month's own `full_outcome_window` flag (which compares against the dataset's end, used only for primary/sensitivity classification)
- `select_popularity_arm(prediction_month)`: same walk-forward rule, restricted to the 5 pure-popularity policies (`POPULARITY_ARM_POLICIES`), tie-break `-recency_weight` — this is the backtest's independent comparison arm
- All hit-rate sweeps are cached per prediction month (`month_hit_rates`) over that month's fixed `evaluable_cases()` cohort, which never depends on which policy is being scored

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `SimilarityEngine.find_similar_teams()` | `src/ml/similarity.py:21` | `PolicyEngine._compute_components()` | `target_team, target_month, k, min_similarity` → `list[(team, score, historical_month)]` |
| `SequenceMapper.learn_sequences_up_to_month()` | `src/ml/sequences.py:121` | `PolicyEngine._compute_components()`, `_month_popularity()` | `max_month` → mutates `transition_matrix`/`practice_popularity`; cached by `max_month` |
| `SequenceMapper.get_typical_next_practices()` | `src/ml/sequences.py:178` | `PolicyEngine._compute_components()`, `explain_practice()` | `practice, top_n` → `list[(practice_name, probability)]` |
| `SequenceMapper.get_practice_popularity()` | `src/ml/sequences.py:242` | `PolicyEngine._month_popularity()` | → `dict[practice, count]`, most-improved first |
| `PolicyEngine.case_components()` | `src/ml/policy.py` | `is_recommendable()`, `evaluable_cases()`, `recommend()` | `team, baseline_month` → cached `CaseComponents` |
| `PolicyEngine.evaluable_cases()` | `src/ml/policy.py` | `month_hit_rates()`, `BacktestEngine` | `prediction_month` → cached `list[CohortCase]`, fixed before any policy scoring |
| `PolicyEngine.select_policy()` / `select_popularity_arm()` | `src/ml/policy.py` | `recommend()`, `BacktestEngine._score_month()` | `prediction_month` → `SelectedPolicy` |
| `PolicyEngine.score_case()` / `top_practices()` | `src/ml/policy.py` | `recommend()`, `month_hit_rates()`, backtest | `CaseComponents, Policy` → `dict[practice, score]` / top-2 tuple |
| `PolicyEngine.recommend()` | `src/ml/policy.py` | `RecommendationEngine.recommend()` | `team, prediction_month` → `RecommendationResult` |
| `PolicyEngine.explain_practice()` | `src/ml/policy.py` | `RecommendationEngine.get_recommendation_explanation()` | `team, prediction_month, practice` → explanation dict |
| `policy_summary()` | `src/ml/policy.py` (module function) | `BacktestEngine`, `APIService.get_recommendations()` | `SelectedPolicy` → serializable audit dict (peer_count/min_similarity are `None` on bootstrap) |
| `RecommendationEngine.recommend()` | `src/ml/recommender.py` | `APIService.get_recommendations()`, `BacktestEngine`, CLI | `target_team, prediction_month` → `RecommendationResult` (thin delegation to `PolicyEngine`) |

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations` (primary consumer of recommendations), `/uc-02-run-backtest-validation` (calls `PolicyEngine` per prediction month)
- **Related Domain Skills:** `/domain-data` (provides `DataProcessor` and team histories), `/domain-validation` (wraps `PolicyEngine` for the backtest), `/domain-api` (exposes recommendations via REST)
