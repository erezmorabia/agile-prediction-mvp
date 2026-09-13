# Frozen Research Protocol

Frozen on 2026-09-12 before producing the XP 2027 evidence extension.

## Post-freeze reporting amendment

The prespecified primary analysis remains unchanged. Following manuscript review, a stricter sensitivity analysis was
added that retains only outcome-bearing primary cases with three observed team-level future snapshots. It removes one
case and may not replace the primary result based on favorability. Bootstrap intervals are explicitly described as
conditional on the monthly policies fitted to the observed histories because policy selection is not repeated inside
each resample.

An exploratory all-recommendable analysis was subsequently added across all 298 cases with exactly three observed
future team snapshots, including the 178 cases with no eligible recorded increase. Those cases contribute zero observed
alignment to every method. This post-protocol analysis estimates realized retrospective alignment across recommendable
cases; it does not replace the primary conditional estimand and does not predict whether improvement will occur.

A second post-protocol robustness analysis repeats the complete walk-forward choice among the unchanged 675-policy grid
inside each of 10,000 team-cluster bootstrap replicates. Each replicate reselects from only those prior prediction
months whose outcome windows had closed; the first three primary months retain the fixed bootstrap policy. This analysis
adds policy-selection variability and cannot replace the prespecified fixed-selection intervals.

## Research questions

1. How effectively can organization-specific maturity histories identify practices associated with a team's next
   observed improvement under leakage-free walk-forward evaluation?
2. What incremental value and stability do similarity and practice-transition evidence provide beyond time-aware
   organizational popularity?

## Claims and exclusions

The study evaluates retrospective ranking alignment conditional on at least one observed improvement. It does not test
whether showing recommendations causes improvement, shortens adoption time, estimates calibrated success probability,
or generalizes beyond the observed organization.

## Primary analysis

- Unit: an evaluable team-prediction-month with at least two non-maxed candidates and at least one observed improvement
  in the next three recorded snapshots after its baseline.
- Scope: prediction months whose three-snapshot outcome window is globally complete.
- Model: the existing globally selected monthly three-factor policy.
- Metric: monthly macro-average Conditional Hit Rate@2.
- Comparators: candidate-aware exact random expectation and independently walk-forward-selected time-aware popularity.
- Selection boundary: a prior prediction month may inform a policy only after its complete outcome window closed before
  the target prediction month.

## Secondary and robustness analyses

- Precision@2, Recall@2, MRR, recommendation coverage, and pooled descriptive hit rate.
- Historical-only popularity, recent-only popularity, similarity-only, transition-only, equal three-factor blend, and
  two-factor equal-weight ablations.
- Primary globally complete scope and all-month sensitivity scope.
- Explicit reporting of bootstrap-policy versus genuinely mixed-policy months.
- Strict cohort audit requiring three team-level future snapshots; no hit-rate interpretation for no-improvement cases.
- Post-protocol exploratory observed alignment across all recommendable cases with three team-level future snapshots,
  assigning zero alignment when no eligible increase was recorded.
- Post-protocol team-cluster bootstrap that repeats walk-forward blend and popularity policy selection within every
  replicate while preserving outcome-closure boundaries.

## Uncertainty

Use 10,000 paired team-cluster bootstrap replicates with seed 22997. Sample team identities with replacement and retain
all cases for each sampled team. Recompute each month's mean and then the monthly macro-average for the model-baseline
difference. Report percentile 95% intervals; do not convert an interval into a causal or universal claim.

The selection-refit robustness analysis uses seed 22999 and the same team-cluster unit. It reselects the blend and
popularity policies inside each replicate before evaluating later months.

## Anti-cherry-picking rule

All frozen primary and secondary outputs are reported. Analyses added after this freeze are labeled exploratory and may
not replace the headline solely because their results are more favorable.

## Fixed ablation configurations

- Historical and recent popularity use 100% popularity with recency weights 0 and 1 respectively.
- Similarity-only and transition-only use 100% of the named factor.
- The equal three-factor analysis assigns one third to each factor.
- Two-factor ablations assign 50% to each included factor and 0% to the excluded factor.
- Fixed ablations use 10 peers, a 0.5 similarity threshold, and 0.5 popularity recency unless that parameter is
  irrelevant or explicitly varied above. These are descriptive robustness checks, not separately tuned competitors.
