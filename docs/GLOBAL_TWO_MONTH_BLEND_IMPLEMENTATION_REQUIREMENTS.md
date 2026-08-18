# Requirement: Global Two-Month Adaptive Recommendation Blend

## Objective

Replace the application's primary recommendation policy with one globally selected, time-aware blend of three evidence sources:

1. Similarity evidence from comparable teams.
2. Practice-transition (sequence) evidence from the target team's recent improvements.
3. Organization-wide popularity evidence.

The policy is selected once for each prediction month from prior completed outcomes and is then applied consistently to every eligible team in that month. It is not selected separately for individual teams.

The primary flow must always return exactly **two** recommendations. The recommendation-count control must not allow a different value for this flow. Requests that ask this primary flow for any number other than two must receive a clear validation error rather than silently receiving a different policy.

## Scope

This requirement applies to the primary recommendation flow and to its historical backtest. The backtest must replay the same month-specific policy that the live recommendation flow would have selected at that point in time.

Remove the user-facing static “best” or “optimal configuration” control and remove the product logic that searches all available historical months to produce one static recommendation configuration. The global monthly policy selection defined in this requirement is the only configuration authority for the primary recommendation flow and its backtest.

The following are out of scope:

- Per-team selection of model settings or blend weights.
- A blend with more granular than 25-percentage-point factor weights.
- Changing the three-snapshot outcome window used to evaluate a recommendation.
- Claiming that the blend is proven superior to time-aware popularity; the current result remains exploratory until later unseen data is available.
- Retaining the static all-history configuration optimizer as a user-facing or primary-flow capability.

## Fixed Component Windows

Both component windows are fixed at two observed snapshots:

- **Similarity look-ahead:** when a historical peer state is comparable to the target team's baseline state, consider improvements by that peer in its next two observed snapshots, provided those snapshots are not later than the target baseline.
- **Sequence recency:** identify practices the target team improved relative to the target baseline during the two immediately preceding observed snapshots.

The component windows must not vary by team or prediction month.

## Score Components

For every candidate practice that is not already at maximum maturity for the target team, calculate normalized component scores.

### Similarity score

Use the target team's baseline maturity profile to find comparable teams only from snapshots available before the baseline. A comparable peer contributes evidence for practices it improved during the two-snapshot look-ahead described above.

For each prediction month, select one global peer-count value and one global minimum-similarity threshold from these candidate sets:

- Peer count: 5, 10, or 19.
- Minimum similarity threshold: 0.00, 0.50, or 0.75.

### Sequence score

Learn organization-wide practice-transition patterns only from observations before the target baseline. Use the target team's improvements in its two preceding observed snapshots to identify likely following practices.

### Time-aware popularity score

Popularity is an organization-wide score, restricted to practices not already complete for the target team. It combines:

- **Historical popularity:** organization-wide practice-improvement frequency available before the target baseline.
- **Recent popularity:** organization-wide practice improvements in the immediately preceding observed transition, from the prior snapshot to the target baseline.

Both popularity inputs must be normalized across eligible practices. Compute time-aware popularity as:

`popularity = recency_weight × recent_popularity + (1 − recency_weight) × historical_popularity`

Select `recency_weight` only from: 0%, 25%, 50%, 75%, or 100%.

## Final Recommendation Score

For each candidate practice, calculate:

`final_score = similarity_weight × similarity_score + sequence_weight × sequence_score + popularity_weight × time_aware_popularity_score`

The three factor weights must total exactly 100%. Select only the 15 combinations formed from 0%, 25%, 50%, 75%, and 100% that sum to 100%.

This includes the pure time-aware-popularity policy: 0% similarity, 0% sequence, and 100% popularity. It must remain a candidate in every monthly selection.

Rank eligible practices by `final_score` and return the two highest-ranked practices. Ties must be deterministic.

## Global Monthly Policy Selection

For a target prediction month, choose one global policy using only earlier prediction months whose full three-snapshot outcome windows had already completed before the target month.

One candidate policy consists of:

- one peer-count value;
- one minimum-similarity threshold;
- one valid similarity / sequence / popularity weight triple; and
- one popularity recency weight.

The candidate policy set contains 675 combinations: 3 peer counts × 3 similarity thresholds × 15 factor-weight triples × 5 recency weights.

Evaluate candidate policies against the same eligible team-month population and select the policy with the highest mean monthly HR@2 across completed prior prediction months. A policy must not be selected using the target month's outcome or any later outcome.

When no prior prediction month has a completed three-snapshot outcome window, use this bootstrap policy:

- Similarity: 0%.
- Sequence: 0%.
- Popularity: 100%.
- Popularity recency: 50% recent and 50% historical.

If candidate policies tie on the selection metric, resolve the tie deterministically, preferring the more popularity-heavy policy and then the lower recency setting. The selected policy must be reproducible from the same dated input data.

## Time Boundaries and Outcome Definition

For a prediction with baseline snapshot `B` and target snapshot `T`:

- Feature generation may use only data at or before `B` and must not use observations after `B`.
- A recommendation is evaluated as correct when at least one of its two practices improves between `B` and any of `T`, the next observed snapshot, or the following observed snapshot.
- A prior prediction month can inform selection for the current target month only after all three of those outcome snapshots are available and precede the current target month.

The application must retain this outcome definition for historical evaluation even though the component windows are fixed at two snapshots.

## User-Visible Explanation and Audit Record

For every prediction month, make the selected global policy available in the recommendation result and backtest result:

- peer count and minimum-similarity threshold;
- fixed two-snapshot component windows;
- similarity, sequence, and popularity percentages;
- popularity recency percentage;
- whether the bootstrap policy was used.

For each returned practice, provide the final score and enough explanation to identify which of similarity, sequence, and popularity contributed to it. Existing team-specific explanations should remain available where applicable.

## Backtest Reporting

The backtest must report, by prediction month:

- the selected global policy;
- number of eligible team-month cases;
- HR@2 for the selected blend;
- HR@2 for independently selected time-aware popularity on the same cohort; and
- the difference between the two.

Primary aggregate reporting must include only months with complete three-snapshot outcome windows. Months without a complete outcome window may be shown separately as sensitivity results and must be labelled as such.

## Acceptance Criteria

```gherkin
Scenario: Return exactly two primary recommendations
  Given a user requests primary recommendations for an eligible team and month
  When the recommendation is generated
  Then exactly two eligible practices are returned
  And a request for a different number of primary recommendations is rejected with a clear validation error

Scenario: Use one global policy for a prediction month
  Given multiple eligible teams are predicted for the same target month
  When the monthly policy has been selected
  Then every team uses the same peer count, similarity threshold, factor weights, and popularity-recency weight
  And the underlying scores and ranked practices may still differ by team

Scenario: Keep the component windows fixed at two snapshots
  Given a recommendation baseline snapshot
  When similarity and sequence scores are calculated
  Then peer improvements are considered for no more than the next two eligible peer snapshots
  And sequence triggers are based on no more than the target team's two preceding observed snapshots

Scenario: Calculate time-aware popularity
  Given an eligible practice and a recommendation baseline snapshot
  When popularity is calculated
  Then the score combines historical organization-wide popularity with popularity from the immediately preceding observed transition
  And the selected recency weight is one of 0%, 25%, 50%, 75%, or 100%

Scenario: Blend the three factors
  Given normalized similarity, sequence, and time-aware popularity scores
  When a final practice score is calculated
  Then the similarity, sequence, and popularity weights total exactly 100%
  And the ranking is based on the resulting weighted score

Scenario: Select the monthly policy without future information
  Given a target prediction month
  When the global policy is selected
  Then only earlier prediction months with complete three-snapshot outcomes are considered
  And no target-month or later outcome is used to select the policy

Scenario: Use the bootstrap policy before completed outcomes exist
  Given no earlier prediction month has a completed three-snapshot outcome window
  When primary recommendations are generated
  Then the policy uses 100% popularity
  And popularity uses 50% recent and 50% historical evidence

Scenario: Keep the primary backtest comparable
  Given a historical backtest is run
  When a primary aggregate result is presented
  Then it includes only prediction months with complete three-snapshot outcome windows
  And it reports the selected blend and time-aware popularity on the same eligible cohort

Scenario: Remove static all-history configuration optimization
  Given a user opens the primary recommendation experience
  When the available recommendation controls are displayed
  Then no static best or optimal configuration control is available
  And the recommendation flow does not use a configuration selected from all historical months
  And only the globally selected month-specific policy controls recommendations
```
