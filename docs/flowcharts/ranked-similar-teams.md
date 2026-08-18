# Flowchart — Comparable Peers → Similarity Component Score

The similarity component is prepared by `PolicyEngine` and scored under the peer count and
minimum-similarity threshold selected for the prediction month. It is one of three components in
the final blend; it does not by itself decide the recommendations.

**Location**: `src/ml/policy.py` (`_compute_components()`, `_selected_peer_indices()`, and
`score_case()`)

```mermaid
flowchart TD
    A[Get target team's baseline maturity vector] --> B[Find all distinct comparable teams at earlier snapshots]
    B --> C[Keep each peer's highest-similarity historical snapshot]
    C --> D[Sort peers by similarity and cache their evidence]
    D --> E[Apply this month's minimum-similarity threshold]
    E --> F[Keep this month's selected top K peers]
    F --> G{Any selected peers?}
    G -->|no| H[Similarity score is zero for every candidate]
    G -->|yes| I[For each selected peer, inspect at most its next two observed snapshots]
    I --> J{Would a snapshot be later than the target baseline?}
    J -->|yes| K[Stop that peer's look-ahead]
    J -->|no| L[For each improved practice, retain the peer's largest improvement]
    L --> M[Add similarity × improvement magnitude to that practice]
    K --> N[Normalize accumulated similarity scores]
    M --> N
    H --> O[Pass similarity component to the three-factor blend]
    N --> O
```

## Notes

- `SimilarityEngine.find_similar_teams()` searches only snapshots before the baseline and returns
  `(team, similarity, historical_month)` tuples. `PolicyEngine` initially retains all available
  peers so that each monthly policy can apply its own `K` and threshold without recomputing them.
- `K` is one of 5, 10, or 19; the threshold is 0.00, 0.50, or 0.75. Both are global settings for
  the prediction month, selected alongside the blend weights.
- The two-snapshot peer look-ahead is fixed. It must never use a peer observation later than the
  target team's baseline, which prevents future information from influencing the score.
- A peer may contribute to several practices, but contributes only its largest observed improvement
  for each practice in that look-ahead window. Contributions from different peers accumulate.
