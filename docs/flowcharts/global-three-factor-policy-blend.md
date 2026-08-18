# Flowchart — Global Three-Factor Policy Blend → Ranked Recommendations

`PolicyEngine` produces the primary recommendations.  For a prediction month it selects one
global policy, then uses that same policy for every recommendable team in the month.  The policy
combines similarity, sequence, and time-aware popularity evidence; it is not a fixed 70/30 blend
and callers cannot tune it per request.

**Location**: `src/ml/policy.py` (`select_policy()`, `score_case()`, and `top_practices()`)

```mermaid
flowchart TD
    A[Receive team and prediction month] --> B[Find the team's usable baseline snapshot]
    B --> C{At least two non-maxed candidate practices?}
    C -->|no| Z[Return clear no-recommendations message]
    C -->|yes| D[Select this month's one global policy]
    D --> E{Earlier prediction month with a completed<br/>three-snapshot outcome window?}
    E -->|no| F["Use bootstrap: 100% popularity,<br/>50% recent / 50% historical"]
    E -->|yes| G[Choose best of 675 policies by mean prior HR@2]
    F --> H[Build component scores for every candidate practice]
    G --> H
    H --> I[Similarity: selected peers' fixed two-snapshot improvements]
    H --> J[Sequence: practices following the team's improvements<br/>in its two preceding observed snapshots]
    H --> K[Popularity: combine historical and immediately recent<br/>organization-wide improvement counts]
    I --> L[Normalize similarity evidence]
    J --> M[Normalize sequence evidence]
    K --> N[Apply the policy's selected recency weight]
    L --> O[Weighted three-factor final score]
    M --> O
    N --> O
    O --> P[Rank eligible practices by score,<br/>then practice name to break ties]
    P --> Q[Return exactly the top 2]
```

## Notes

- **One policy for a month, not a team.** A policy contains peer count, minimum similarity,
  similarity / sequence / popularity weights, and popularity recency weight. The candidate grid is
  `3 × 3 × 15 × 5 = 675` policies. `select_policy()` uses only completed earlier prediction-month
  outcomes; when none exist, it uses the stated bootstrap policy.
- **Fixed component windows.** Similarity examines at most the next two observed peer snapshots,
  without going past the target baseline. Sequence uses the target team's two preceding observed
  snapshots. Only the policy weights and peer parameters can change month to month.
- **Research-exact normalization.** Similarity and sequence evidence are normalized before the
  candidate mask. Historical popularity is masked then normalized; recent popularity is normalized
  organization-wide then masked. See `PolicyEngine.score_case()` for the precise implementation.
- **No peers is not an error.** If a selected threshold leaves no peers, similarity is zero while
  sequence and popularity still rank the two recommendations.
- **Factor weights always sum to 100%.** They are selected from the 15 combinations using
  0%, 25%, 50%, 75%, and 100% increments.
