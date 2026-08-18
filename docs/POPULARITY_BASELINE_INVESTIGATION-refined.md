# Beating the Popularity Baseline — Investigation Summary

## Background

The production system recommends up to `top_n` agile practices for a team to work on next using collaborative filtering and practice-transition sequences. Its reported 50.3% accuracy was selected and measured on the same 10-month dataset, creating optimization bias.

This refinement preserves the investigation's finding: no legitimate no-future-leak configuration search tried so far beats the popularity baseline in aggregate. It defines the next evaluation work without changing production recommendations.

## Dataset

- 10 months from `2020-01-07` through `2020-11-04`; 87 teams and 30 retained practices.
- `top_n=2` is a fixed operational constraint.
- The rolling backtest begins at `2020-05-03`, yielding seven currently eligible test months.
- The intended outcome window is the test month plus the following two months.

## Metric definitions

- **Accuracy (HR@2):** a team/month is correct when either recommendation improves within its outcome window; overall accuracy is the macro-average of monthly accuracy.
- **Popularity baseline:** recommend the two practices improved most often organization-wide from data available before the prediction point, excluding practices already maxed out for that team.
- **Primary success criterion:** a policy must have a strictly positive macro-averaged `popularity_gap` over the primary test population.

## Established findings

- The circular fixed configuration scores 50.3% versus a 43.6% popularity baseline, but loses in three of seven months.
- Legitimate walk-forward searches, including wider grids and both random- and popularity-gap selection criteria, did not beat popularity in aggregate; the best documented result is 42.6% versus 44.5%.
- Popularity is learned only from prior months by `learn_sequences_up_to_month`, so it is a valid and difficult baseline rather than a leakage artifact.
- The likely constraint is limited historical sample size, not parameter-grid coverage.

## Goal

Validate—not deploy—three pre-specified adaptive recommendation policies using a no-future-leak nested walk-forward evaluation. The work succeeds only if a policy strictly beats the popularity baseline in aggregate; per-month results are reported as diagnostics, not a separate pass/fail requirement.

## Evaluation design

For each eligible outer test month:

1. Use only data before that month to select any policy thresholds or score weights.
2. Generate that month's recommendations without accessing its outcomes.
3. Evaluate recommendations against the existing outcome-window definition.
4. Record the policy's monthly HR@2 and popularity baseline HR@2.

Evaluate every policy as its own pre-specified arm. Do not select a winner after observing all outer-test outcomes and present it as confirmed. Any apparent winner is exploratory until confirmed with new data.

The primary result uses only months with a fully observed three-month outcome window. Report the existing seven-month, shortened-final-window result separately as a sensitivity analysis.

## Pre-specified policies to evaluate

### 1. Switch policy

Return two popularity recommendations when a convergence signal computed exclusively from prior months indicates highly synchronized organization-wide behavior; otherwise return two personalized similarity/sequence recommendations.

### 2. Split policy

Return one eligible popularity recommendation and one distinct eligible personalized recommendation. Define a deterministic tie and duplicate-resolution rule before evaluation.

### 3. Score-blend policy

Combine popularity and personalized pre-outcome scores into one deterministic ranking and return the top two eligible practices. Learn any blending weight only from data before the outer test month.

## Acceptance Criteria — Added During Refinement

```gherkin
Scenario: Evaluate a pre-specified policy without future leakage
  Given a policy and an outer test month
  When its thresholds or weights and its recommendations are produced
  Then only observations before the outer test month are used
  And the month's outcomes are used only after recommendations are fixed

Scenario: Compare all adaptive policies fairly
  Given the switch, split, and score-blend policies
  When the nested walk-forward evaluation completes
  Then each policy has a separately reported macro-averaged HR@2 and popularity gap
  And no post-hoc winner is presented as confirmed without new-data validation

Scenario: Report unequal outcome windows transparently
  Given a test month with all three outcome months observed
  When primary results are calculated
  Then it is included in the primary comparison
  And all seven currently eligible months are reported separately as a sensitivity analysis

Scenario: Qualify a promising policy
  Given a completed primary comparison
  When a policy's macro-averaged popularity gap is calculated
  Then it qualifies as promising only when the gap is strictly greater than zero
  And its month-by-month results are retained as diagnostics
```

## Out of Scope

- Changing the production recommender or its live recommendation behavior.
- Claiming that an exploratory winner is a confirmed improvement without additional unseen data.
