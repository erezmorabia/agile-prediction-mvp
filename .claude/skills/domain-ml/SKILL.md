---
name: domain-ml
description: ML engine: collaborative filtering (cosine similarity), Markov chain sequences, and hybrid scoring. Use when modifying recommendation logic, similarity search, sequence learning, or scoring/normalization.
---

# Domain: ML

## Summary
Three tightly coupled components produce hybrid practice recommendations: `SimilarityEngine` finds peers via cosine similarity, `SequenceMapper` learns Markov transitions between improvements, and `RecommendationEngine` combines both signals with weighted scoring.

## Data Flows

- **Recommendation:** `RecommendationEngine.recommend()` → `SequenceMapper.learn_sequences_up_to_month(current_month)` → `SimilarityEngine.find_similar_teams(target_team, current_month)` → for each similar team check improvements in next 1–3 months (capped at current_month) → apply sequence boost from recently improved practices → normalize each component separately → combine with weights → filter maxed-out practices → return top N
- **Explanation:** `get_recommendation_explanation()` runs the same similarity + sequence lookup but returns a breakdown dict (similar_teams_list, improved_count, has_sequence_boost) instead of ranked scores
- **Sequence cache:** `learn_sequences_up_to_month(max_month)` stores results in `_sequence_cache[max_month]`; subsequent calls with the same max_month return from cache, avoiding recomputation across backtest iterations

## Domain Validation Rules and Business Logic

- Only data from months **< current_month** is used for sequence learning and similarity matching (data leakage prevention)
- Similar teams deduplicated by team name — only the highest-similarity historical snapshot is kept per team
- Practices at normalized score ≥ 1.0 are excluded from recommendations (already at max maturity)
- `allow_first_three_months=True` bypasses the month-1 guard; used only by backtest engine

## Formulas / Scoring / Calculation Logic

**Hybrid scoring:**
```
final_score = similarity_weight × norm_sim_score + (1 − similarity_weight) × norm_seq_score
```
- `similarity_weight` default: **0.6** (60% similarity, 40% sequence)
- Each component normalized independently to [0, 1] before combining
- Combined scores normalized again to [0, 1] before returning

**Similarity score (per practice):**
```
similarity_scores[practice] += similarity_score × improvement_magnitude
```
- `improvement_magnitude` = max improvement across the 1–3 month lookahead window

**Sequence score (per practice):**
```
sequence_scores[practice] += transition_probability
```
- Summed across all recently-improved practices that have a transition to this practice

**Default tunable parameters** (all in `RecommendationEngine.recommend()`):
| Parameter | Default | Effect |
|---|---|---|
| `top_n` | 2 | Recommendations returned |
| `k_similar` | 19 | Similar teams considered |
| `similarity_weight` | 0.6 | Similarity vs sequence balance |
| `similar_teams_lookahead_months` | 3 | Months ahead to check for improvements |
| `recent_improvements_months` | 3 | Months back to detect recent improvements |
| `min_similarity_threshold` | 0.75 | Min cosine similarity to include a team |

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `SimilarityEngine.find_similar_teams()` | `src/ml/similarity.py:86` | `RecommendationEngine.recommend()` | `target_team, target_month, k, min_similarity` → `list[(team, score, historical_month)]` |
| `SequenceMapper.learn_sequences_up_to_month()` | `src/ml/sequences.py:99` | `RecommendationEngine.recommend()`, `BacktestEngine.run_backtest()` | `max_month` → mutates `transition_matrix`; cached by `max_month` |
| `SequenceMapper.get_typical_next_practices()` | `src/ml/sequences.py:179` | `RecommendationEngine.recommend()` | `practice, top_n` → `list[(practice_name, probability)]` |
| `RecommendationEngine.recommend()` | `src/ml/recommender.py:25` | `APIService.get_recommendations()`, `BacktestEngine` | `target_team, current_month, top_n, k_similar, ...` → `list[(practice, score, current_level)]` |
| `RecommendationEngine.get_recommendation_explanation()` | `src/ml/recommender.py:293` | `APIService.get_recommendations()` | `target_team, current_month, practice` → explanation dict |

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations` (primary consumer of recommendations), `/uc-02-run-backtest-validation` (calls recommender in a loop), `/uc-03-run-parameter-optimization` (tunes ML parameters)
- **Related Domain Skills:** `/domain-data` (provides `DataProcessor` and team histories), `/domain-validation` (wraps recommender for backtest/optimization), `/domain-api` (exposes recommendations via REST)
