# Requirement: Global Two-Month Adaptive Recommendation Blend

## Objective

Replace the application's primary recommendation policy with one globally selected, time-aware blend of three evidence sources:

1. Similarity evidence from comparable teams.
2. Practice-transition (sequence) evidence from the target team's recent improvements.
3. Organization-wide popularity evidence.

The policy is selected once for each prediction month from prior completed outcomes and is then applied consistently to every eligible team in that month. It is not selected separately for individual teams.

The primary flow must always return exactly **two** recommendations. The recommendation-count control must not allow a different value for this flow. Requests that ask this primary flow for any number other than two must receive a clear validation error rather than silently receiving a different policy. There is no user-facing control for the recommendation count in the web interface, so this validation applies to the request interface itself.

## Scope

This requirement applies to the primary recommendation flow and to its historical backtest. The backtest must replay the same month-specific policy that the live recommendation flow would have selected at that point in time.

The command line interface is part of the primary recommendation flow. Its recommendation command must use the same month-specific global policy and expose the same policy information as the web flow, so that both interfaces produce the same recommendations for the same team and month.

Remove the user-facing static “best” or “optimal configuration” control and remove the product logic that searches all available historical months to produce one static recommendation configuration. The global monthly policy selection defined in this requirement is the only configuration authority for the primary recommendation flow and its backtest.

The static all-history optimizer is removed completely, not only hidden. This includes its engine, its endpoints, its web controls, its command line menu options, and its use case documentation and registration entries.

The backtest must not expose any user-adjustable model parameters. The six existing backtest parameter controls (recommendation count, similarity weight, peer count, look-ahead months, recent months, and minimum similarity threshold) are removed, because the component windows are fixed and the monthly policy is the only configuration authority.

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

## Eligible Team-Month Cases

Two eligibility terms are used, because the live flow cannot know an outcome that has not happened yet.

**Recommendable team-month** — used by the live recommendation flow. A team-month is recommendable when, at the recommendation baseline:

- the team has a usable baseline snapshot; and
- the team has at least two universal candidate practices that were not already at maximum maturity at the baseline.

There is no outcome condition. A recommendable team-month can always be served, including for the most recent prediction month.

**Evaluable team-month** — used by the backtest cohort and by global monthly policy selection. A team-month is evaluable when:

- it is recommendable; and
- the team improved at least one practice within the three-snapshot outcome window.

The evaluable set must be established before any scoring takes place and must be identical for every candidate policy and for every reported comparison arm. It must never depend on what a policy recommended or on whether a policy produced a result.

For sensitivity months whose three-snapshot outcome window is truncated, the evaluable set is built from the outcome snapshots that are actually observed, using the same rule. These months are reported separately and labelled as sensitivity results, and their case counts must not be mixed into the primary aggregate.

## Score Components

For every candidate practice that is not already at maximum maturity for the target team, calculate normalized component scores. This candidate set is the same for all three components: a practice is scored even when only one component gives it a value.

### Similarity score

Use the target team's baseline maturity profile to find comparable teams only from snapshots available before the baseline. A comparable peer contributes evidence for practices it improved during the two-snapshot look-ahead described above.

For each prediction month, select one global peer-count value and one global minimum-similarity threshold from these candidate sets:

- Peer count: 5, 10, or 19.
- Minimum similarity threshold: 0.00, 0.50, or 0.75.

When no comparable peer team is found, the similarity component contributes zero for every candidate practice. This is not an error: the sequence and popularity components still rank the practices, and two recommendations are still returned.

### Sequence score

Learn organization-wide practice-transition patterns only from observations before the target baseline. Use the target team's improvements in its two preceding observed snapshots to identify likely following practices.

### Time-aware popularity score

Popularity is an organization-wide score, restricted to practices not already complete for the target team. It combines:

- **Historical popularity:** organization-wide practice-improvement frequency available before the target baseline.
- **Recent popularity:** organization-wide practice improvements in the immediately preceding observed transition, from the prior snapshot to the target baseline.

Both popularity inputs must be normalized across eligible practices. Compute time-aware popularity as:

`popularity = recency_weight × recent_popularity + (1 − recency_weight) × historical_popularity`

Select `recency_weight` only from: 0%, 25%, 50%, 75%, or 100%.

**Implementation note (deviation from "both popularity inputs must be normalized across eligible
practices" above):** the shipped implementation normalizes historical and recent popularity in
different orders relative to masking against the target team's candidate practices - historical
popularity is masked to candidates *then* normalized, while recent popularity is normalized
organization-wide *then* masked to candidates. This is deliberate: it reproduces
`scripts/research_popularity_strategies.py` / `scripts/research_three_factor_blend.py` byte-for-
byte, which is what the pinned reproduction numbers in
`results/fully-nested-global-fixed-two-month-20260818.json` were generated from. Normalizing both
inputs identically (mask-then-normalize for both) would change every downstream score and was not
adopted, to keep the shipped numbers traceable to the research that validated this protocol.

## Final Recommendation Score

For each candidate practice, calculate:

`final_score = similarity_weight × similarity_score + sequence_weight × sequence_score + popularity_weight × time_aware_popularity_score`

The three factor weights must total exactly 100%. Select only the 15 combinations formed from 0%, 25%, 50%, 75%, and 100% that sum to 100%.

This includes the pure time-aware-popularity policy: 0% similarity, 0% sequence, and 100% popularity. It must remain a candidate in every monthly selection.

Rank eligible practices by `final_score` and return the two highest-ranked practices. Ties must be deterministic.

When a team has fewer than two universal candidate practices that are not already at maximum maturity, the primary flow returns no recommendations and shows a clear message stating that the team has fewer than two practices left to improve. Such a team-month is neither recommendable nor evaluable, so the live flow and the backtest treat it the same way.

## Global Monthly Policy Selection

For a target prediction month, choose one global policy using only earlier prediction months whose full three-snapshot outcome windows had already completed before the target month.

One candidate policy consists of:

- one peer-count value;
- one minimum-similarity threshold;
- one valid similarity / sequence / popularity weight triple; and
- one popularity recency weight.

The candidate policy set contains 675 combinations: 3 peer counts × 3 similarity thresholds × 15 factor-weight triples × 5 recency weights.

Evaluate candidate policies against the same evaluable team-month population and select the policy with the highest mean monthly HR@2 across completed prior prediction months. A policy must not be selected using the target month's outcome or any later outcome.

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

When the bootstrap policy is used, the peer count and the minimum-similarity threshold are reported as not applicable, because similarity carries 0% weight in that month. No default value is shown in their place.

For each returned practice, provide the final score and enough explanation to identify which of similarity, sequence, and popularity contributed to it. Existing team-specific explanations should remain available where applicable. When no comparable peer team was found, the explanation must say so instead of showing an empty peer list without comment.

## Backtest Reporting

The backtest must report, by prediction month:

- the selected global policy;
- number of evaluable team-month cases;
- HR@2 for the selected blend;
- HR@2 for independently selected time-aware popularity on the same cohort; and
- the difference between the two.

The time-aware popularity comparison arm is selected under the same monthly rule as the blend, restricted to pure popularity policies: for each month, choose the recency weight with the highest mean HR@2 across completed earlier prediction months, using 0% similarity and 0% sequence. The comparison arm must never use the reported month's own outcome.

The existing random baseline, precision@N, recall@N, and MRR figures remain in the backtest report as supporting numbers. The previous static popularity baseline is removed, because the time-aware popularity comparison arm replaces it; the report must show only one popularity comparison.

Primary aggregate reporting must include only months with complete three-snapshot outcome windows. Months without a complete outcome window may be shown separately as sensitivity results and must be labelled as such.

## Acceptance Criteria

```gherkin
Scenario: Return exactly two primary recommendations
  Given a user requests primary recommendations for a recommendable team and month
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
  And it reports the selected blend and time-aware popularity on the same evaluable cohort

Scenario: Remove static all-history configuration optimization
  Given a user opens the primary recommendation experience
  When the available recommendation controls are displayed
  Then no static best or optimal configuration control is available
  And the recommendation flow does not use a configuration selected from all historical months
  And only the globally selected month-specific policy controls recommendations
```

## Acceptance Criteria — Added During Refinement

```gherkin
Scenario: Establish the evaluable population before scoring and independently of any policy
  Given a team-month with a usable baseline snapshot
  When the evaluable population for a prediction month is determined
  Then the team-month is evaluable only if it has at least one observed improvement in the three-snapshot outcome window
  And it is evaluable only if at least two universal candidate practices were below maximum maturity at the baseline
  And the population is decided before any policy scores are calculated
  And the same evaluable cases are used for every candidate policy and for every reported comparison arm

Scenario: Serve the live flow without an outcome condition
  Given the most recent prediction month, whose outcome window has not closed
  When a user requests primary recommendations for a team with a usable baseline
  Then the recommendation is served as long as the team has at least two universal candidate practices below maximum maturity
  And no observed improvement is required to serve it

Scenario: Compare the blend and time-aware popularity on identical cases
  Given a prediction month with a complete three-snapshot outcome window
  When the backtest reports the blend and the time-aware popularity comparison
  Then both results are calculated on exactly the same evaluable team-month cases
  And the reported number of evaluable cases is the same for both

Scenario: Select the time-aware popularity comparison arm under the same monthly rule
  Given a prediction month being reported in the backtest
  When the time-aware popularity comparison arm is prepared
  Then its recency weight is chosen as the one with the highest mean HR@2 across completed earlier prediction months
  And the chosen policy uses no similarity evidence and no sequence evidence
  And the reported month's own outcome is not used to choose it

Scenario: Recommend when no comparable peer team is found
  Given a recommendable team and month where no peer team meets the selected minimum similarity threshold
  When primary recommendations are generated
  Then the similarity contribution is zero for every candidate practice
  And exactly two recommendations are still returned from sequence and popularity evidence
  And the explanation states that no comparable team was found

Scenario: Handle a team with fewer than two practices left to improve
  Given a team whose practices are all at maximum maturity except at most one
  When primary recommendations are requested
  Then no recommendations are returned
  And a clear message explains that the team has fewer than two practices left to improve
  And the team-month is not counted in the backtest evaluable population

Scenario: Report the audit record for a bootstrap month
  Given a prediction month that uses the bootstrap policy
  When the selected policy is shown in the recommendation result or the backtest result
  Then it is marked as using the bootstrap policy
  And the peer count and the minimum similarity threshold are shown as not applicable
  And no default peer count or threshold value is shown in their place

Scenario: Run the backtest without user-adjustable model parameters
  Given a user opens the backtest experience
  When the available controls are displayed
  Then no controls for recommendation count, similarity weight, peer count, look-ahead months, recent months, or minimum similarity threshold are available
  And the backtest uses only the month-specific policy for every prediction month

Scenario: Report supporting metrics alongside the new comparison
  Given a completed backtest run
  When the results are presented
  Then the random baseline, precision, recall, and MRR figures are still reported
  And the previous static popularity baseline is no longer reported
  And exactly one popularity comparison is shown, which is the time-aware popularity arm

Scenario: Produce the same recommendations from the command line as from the web interface
  Given the same recommendable team and prediction month
  When recommendations are requested from the command line interface and from the web interface
  Then both return the same two practices in the same order
  And both show the same selected policy information
  And the command line interface offers no optimal configuration option
```

## Out of Scope

- Keeping the static all-history optimizer in any form, including as an offline research capability or a hidden endpoint. All of the following are removed: the optimization engine; the three optimize endpoints (`POST /api/optimize`, `POST /api/optimize/cancel`, `GET /api/optimize/latest`) together with their rows in the API Endpoints table in `.claude/rules/architecture.md`; the optimizer entries in the Functional Domains table in the same file; the web controls; the command line menu options; and the `uc-03-run-parameter-optimization` skill with its rows in `CLAUDE.md` and `.claude/rules/product.md`.
- Any user-adjustable model parameter on the backtest experience.
- Reporting the previous static popularity baseline next to the new time-aware popularity comparison arm.
